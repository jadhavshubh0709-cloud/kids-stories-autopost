"""Makes one complete Twin Heroes story reel with AI: story -> 3D clips -> narrator voice -> finished reel.

Usage:
  python3 pipeline/make_story_reel.py                     # reel for today (IST)
  python3 pipeline/make_story_reel.py --date 2026-11-25   # a specific date
  python3 pipeline/make_story_reel.py --days 3            # today + next 2 days (skips dates that exist)

Output: reels/<date>/reel.mp4 + caption.txt, specs/<date>.json (the story), content/history.json (to avoid repeats).
Env: GEMINI_API_KEY (required), SCENES (default 5), RESOLUTION (720p), MOCK_GEMINI=1 for an offline test.
"""
import argparse, datetime as dt, glob, json, os, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
import gemini_api, story_writer, assemble

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
HISTORY = os.path.join(ROOT, "content", "history.json")


def load_history():
    return json.load(open(HISTORY)) if os.path.exists(HISTORY) else []


def pick_moral(history):
    used = [h["moral"] for h in history[-len(story_writer.MORALS) + 1:]]
    for m in story_writer.MORALS:
        if m not in used: return m
    return story_writer.MORALS[len(history) % len(story_writer.MORALS)]


def make_clip_with_retry(prompt, refs, out, resolution):
    last = None
    tries = [(prompt, refs), (prompt + "\nKeep it simple, calm and cheerful.", refs)]
    if refs: tries.append((prompt, []))   # some safety filters reject reference images; text-only as last resort
    for attempt, (p, r) in enumerate(tries):
        try:
            return gemini_api.generate_clip(p, r, out, resolution=resolution)
        except gemini_api.ApiError as e:
            last = e; print(f"  clip attempt {attempt + 1} failed: {str(e)[:300]}", flush=True); time.sleep(10)
    raise last


def make_one(date):
    out_dir = os.path.join(ROOT, "reels", date)
    if os.path.exists(os.path.join(out_dir, "reel.mp4")):
        print(f"{date}: already has a reel, skipping"); return False
    history = load_history()
    n = int(os.environ.get("SCENES", "5")); res = os.environ.get("RESOLUTION", "720p")
    work = os.path.join(ROOT, "work", date); os.makedirs(work, exist_ok=True)
    refs = sorted(glob.glob(os.path.join(ROOT, "assets", "characters", "*.png")) +
                  glob.glob(os.path.join(ROOT, "assets", "characters", "*.jpg")))[:3]
    if not refs: print("  note: no character reference images in assets/characters/ (looks may vary between clips)")

    moral = pick_moral(history)
    print(f"{date}: writing a story about '{moral}'", flush=True)
    story = story_writer.write_story(moral, [h["title"] for h in history], n)
    story["story_no"] = (history[-1]["story_no"] + 1) if history else 1
    story["moral"] = moral
    os.makedirs(os.path.join(ROOT, "specs"), exist_ok=True)
    json.dump(story, open(os.path.join(ROOT, "specs", f"{date}.json"), "w"), indent=2, ensure_ascii=False)
    print(f"  Story #{story['story_no']}: {story['title']}", flush=True)

    clips, voices = [], []
    for i, sc in enumerate(story["scenes"]):
        print(f"  scene {i + 1}/{n}: clip + voice", flush=True)
        c = os.path.join(work, f"clip{i}.mp4")
        if not os.path.exists(c): make_clip_with_retry(story_writer.video_prompt(sc), refs, c, res)
        v = os.path.join(work, f"voice{i}.wav")
        if not os.path.exists(v): gemini_api.narrate(sc["narration"], v)
        clips.append(c); voices.append(v)
    mv = os.path.join(work, "voice_moral.wav")
    gemini_api.narrate(f"Remember, {story['moral_line']}", mv)

    os.makedirs(out_dir, exist_ok=True)
    music = os.path.join(ROOT, "music", story["music"] + ".m4a")
    total = assemble.build_reel(story, clips, voices, mv, work, os.path.join(out_dir, "reel.mp4"), music)
    open(os.path.join(out_dir, "caption.txt"), "w").write(story["caption"].strip() + "\n")
    history.append({"date": date, "story_no": story["story_no"], "title": story["title"], "moral": moral})
    json.dump(history, open(HISTORY, "w"), indent=2, ensure_ascii=False)
    shutil.rmtree(work, ignore_errors=True)
    print(f"  done: reels/{date}/reel.mp4 ({total:.1f}s)", flush=True)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date"); ap.add_argument("--days", type=int, default=1)
    a = ap.parse_args()
    start = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(IST).date()
    failed = []
    for k in range(a.days):
        d = (start + dt.timedelta(days=k)).isoformat()
        try:
            make_one(d)
        except Exception as e:
            print(f"{d}: FAILED - {e}", flush=True); failed.append(d)
    if failed: sys.exit(f"Failed dates: {', '.join(failed)}")


if __name__ == "__main__":
    main()
