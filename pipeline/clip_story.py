"""Veo-clip stories (realistic 3D, like the owner's sample): AI writes a 3-scene story with one Veo prompt per scene;
the 3 clips are made with the owner's Gemini Pro (Veo) and dropped in inbox/<date>/; this script adds narrator voice,
subtitles, title, lesson ending and music.

  python3 pipeline/clip_story.py plan  --date D   -> specs/D.json + inbox/D/PROMPTS.md (3 Veo prompts)
  python3 pipeline/clip_story.py build [--date D] -> reels/D/reel.mp4 + caption.txt from inbox/D/1.mp4 2.mp4 3.mp4
                                                     (no --date: every inbox/<date>/ whose clips are all there)
"""
import argparse, datetime as dt, glob, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
import gemini_api, assemble
from make_story_reel import load_history, pick_moral, HISTORY, IST

N = 3
VIDEO_EXT = (".mp4", ".mov", ".webm", ".m4v")

# Same words every day => Veo draws the characters the same way every day.
CAST = {
    "gappu": "Gappu, a small baby elephant with soft blue-grey skin, big pink ears, large shiny brown eyes and a short curly trunk",
    "peeku": "Peeku, a tiny fluffy bright-yellow duckling with an orange beak, orange feet and big round eyes",
    "chiku": "Chiku, a little white bunny with long pink-lined ears, a pink nose and fluffy fur",
    "tara": "Tara, a chubby honey-brown bear cub with round ears and a cream-coloured snout",
    "bandu": "Bandu, a small cheeky brown monkey with a light peach face, big ears and a curly tail",
    "mithu": "Mithu, a little green parrot with a red beak and bright feathers",
}
STYLE = ("Pixar-style 3D animated movie scene, ultra-detailed soft fur and skin textures, big expressive eyes, warm golden-hour "
         "sunlight with soft light rays, shallow depth of field, cinematic slow camera move, vertical 9:16. "
         "Gentle nature sounds only, no speech, no music, no text, no subtitles, no logos.")

PROMPT = """You write very short, heart-warming animated moral stories for the Instagram page @kahani.time.kids (parents of 3-8 year olds in India).
Each story has EXACTLY {n} scenes; each scene becomes ONE 8-second realistic 3D animated clip (like a Pixar short).

Characters you can use (pick 1-2, prefer ones not used recently: {recent_cast}):
{cast}
Only these animal friends appear on screen - no humans.
Moral to teach: {moral}. Gentle and kind: no danger, villains, injuries, punishment or brands. Ends happily.
Settings: beautiful nature (pond, meadow, forest, riverbank, garden, rain, sunset). Do not retell: {recent}

Return JSON only:
{{
  "title": "3-5 word title",
  "cast": ["ids"],
  "moral_line": "the lesson in at most 6 simple words",
  "question": "one short question for parents",
  "music": "gentle" or "playful" or "adventure",
  "caption": "1 hook line with 1-2 emoji, blank line, a question for parents, blank line, 'A new story every day ✨ Follow @kahani.time.kids', blank line, 8 hashtags ending with #kahanitimekids",
  "scenes": [
    {{"shot": "what the 8-second clip shows: setting, what the characters do, their expressions, camera (close-up / wide / slow push-in). 40-70 words. ONE simple action per clip.",
      "narration": "what the storyteller says over this clip: 1-2 very simple sentences, 10-20 words"}}
  ]
}}"""


def veo_prompt(story, scene):
    who = " ".join(CAST[c] + "." for c in story["cast"] if c in CAST)
    return f"{STYLE}\nCharacters: {who}\nScene: {scene['shot']}"


def plan(date):
    spec_path = os.path.join(ROOT, "specs", f"{date}.json")
    if os.path.exists(spec_path):
        story = json.load(open(spec_path))
    else:
        history = load_history(); moral = pick_moral(history)
        recent_cast = [c for h in history[-4:] for c in h.get("cast", [])]
        cast = "\n".join(f"  {k}: {v}" for k, v in CAST.items())
        prompt = PROMPT.format(n=N, cast=cast, recent_cast=", ".join(recent_cast) or "none", moral=moral,
                               recent=", ".join(h["title"] for h in history[-30:]) or "none")
        for _ in range(3):
            story = gemini_api.generate_json(prompt)
            story["cast"] = [c for c in story.get("cast", []) if c in CAST] or ["gappu", "peeku"]
            if len(story.get("scenes", [])) == N and all(s.get("shot") and s.get("narration") for s in story["scenes"]): break
        story["scenes"] = story["scenes"][:N]
        story.update(story_no=(history[-1]["story_no"] + 1) if history else 1, moral=moral, kind="veo")
        story["caption"] = story["caption"].replace("#twinheros", "#kahanitimekids")
        if "#kahanitimekids" not in story["caption"]: story["caption"] = story["caption"].rstrip() + " #kahanitimekids"
        for sc in story["scenes"]: sc["veo_prompt"] = veo_prompt(story, sc)
        os.makedirs(os.path.dirname(spec_path), exist_ok=True)
        json.dump(story, open(spec_path, "w"), indent=2, ensure_ascii=False)
        history.append({"date": date, "story_no": story["story_no"], "title": story["title"], "moral": moral, "cast": story["cast"]})
        json.dump(history, open(HISTORY, "w"), indent=2, ensure_ascii=False)
    lines = [f"# Story #{story['story_no']}: {story['title']} ({date})", "", f"Lesson: {story['moral_line']}", "",
             f"Make {N} videos in the Gemini app (Veo), one per prompt, vertical 9:16. Save them as 1.mp4, 2.mp4, 3.mp4 and upload to",
             f"https://github.com/jadhavshubh0709-cloud/kids-stories-autopost/upload/main/inbox/{date}", ""]
    for i, sc in enumerate(story["scenes"], 1):
        lines += [f"## Clip {i}", f"Narrator: \"{sc['narration']}\"", "", "```", sc["veo_prompt"], "```", ""]
    os.makedirs(os.path.join(ROOT, "inbox", date), exist_ok=True)
    open(os.path.join(ROOT, "inbox", date, "PROMPTS.md"), "w").write("\n".join(lines))
    print(f"{date}: Story #{story['story_no']} '{story['title']}' planned")
    return story


def clips_for(date):
    files = [f for f in glob.glob(os.path.join(ROOT, "inbox", date, "*")) if f.lower().endswith(VIDEO_EXT)]
    num = {}
    for f in files:
        m = re.match(r"\D*(\d+)", os.path.basename(f))
        if m: num.setdefault(int(m.group(1)), f)
    if all(i in num for i in range(1, N + 1)): return [num[i] for i in range(1, N + 1)]
    if len(files) >= N and not num: return sorted(files)[:N]
    return None


def build(date):
    spec_path = os.path.join(ROOT, "specs", f"{date}.json")
    out = os.path.join(ROOT, "reels", date, "reel.mp4")
    if not os.path.exists(spec_path) or os.path.exists(out): return False
    story = json.load(open(spec_path))
    if story.get("kind") != "veo": return False
    clips = clips_for(date)
    if not clips:
        print(f"{date}: waiting for {N} clips in inbox/{date}/"); return False
    work = os.path.join(ROOT, "work", date); os.makedirs(work, exist_ok=True)
    lines = [s["narration"].strip() for s in story["scenes"]] + [f"Remember, {story['moral_line']}"]
    full = os.path.join(work, "voice_full.wav")
    gemini_api.narrate("  ...  ".join(lines), full)                      # one voice request
    segs = assemble.split_by_pauses(full, len(lines), work, [len(l.split()) for l in lines])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    total = assemble.build_reel(story, clips, [w for w, _ in segs[:-1]], segs[-1][0], work, out,
                                os.path.join(ROOT, "music", story.get("music", "gentle") + ".m4a"))
    open(os.path.join(os.path.dirname(out), "caption.txt"), "w").write(story["caption"].strip() + "\n")
    shutil.rmtree(work, ignore_errors=True)
    print(f"{date}: reel ready ({total:.1f}s)")
    return True


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("action", choices=["plan", "build"]); ap.add_argument("--date")
    a = ap.parse_args()
    if a.action == "plan":
        plan(a.date or dt.datetime.now(IST).date().isoformat())
    else:
        dates = [a.date] if a.date else sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "inbox", "*")) if os.path.isdir(p))
        for d in dates: build(d)


if __name__ == "__main__":
    main()
