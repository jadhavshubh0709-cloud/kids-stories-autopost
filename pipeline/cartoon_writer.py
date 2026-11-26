"""AI writes a story AND stages it for the cartoon engine (who stands where, what they do, which props appear).
The model only picks from simple menus; `stage()` turns those choices into exact positions, so scenes always look right."""
import gemini_api
from cartoon_engine import ACTS, MOODS, PROPS, CAST

PROMPT = """You write and stage very short animated moral stories for the Instagram page @kahani.time.kids
(parents of 3-8 year olds in India).

CHARACTERS you can use (pick 1-3 for this story, and prefer ones not used in recent stories: {recent_cast}):
{cast}
Adults (Maa, Papa, Dadi, teacher) may be mentioned in narration but are never on screen.

{source}

Write the story as a loved children's picture-book author would (think Julia Donaldson or a Pixar short).
- Moral to teach: {moral}
- Gentle and kind: no villains, danger, punishment, brands or real people. Ends happily. Simple English, Indian everyday life.
- Do not retell these recent stories: {recent}

WHAT MAKES IT A GOOD STORY (most important):
- Build it around ONE small, real feeling every child knows: feeling left out, being too small, losing a game,
  breaking something, being jealous, shy on the first day, wanting something RIGHT NOW, being scared of the dark.
- Give it a specific, surprising situation, not a generic "they played and shared" or "she saw a hungry animal and fed it".
- Give the main character one wish or worry and one lovable quirk (always counting things, giggles like hiccups...).
- Shape: scene 1 = hook (character + problem in the first sentence, make kids curious);
  middle = the character tries, it goes wrong or feels hard, the feeling grows;
  turning point = the character CHOOSES the kind / brave / honest thing themselves (no adult fixes it);
  last scene = a warm ending that makes a parent smile (a hug, a shared laugh, a cosy image).
- SHOW the moral through what happens. Never state it in the narration ("and so she learned that..." is forbidden).
- Use one short repeated line or sound kids can say along (e.g. "Not yet, not yet!"), heard at least twice.
- Every scene must move the story forward. Vivid simple words: sounds, colours, feelings.
- The story must make sense to a parent watching: every event follows from the one before, and characters act
  believably (animals eat what they really eat: no mango for a puppy; a puppy wants a ball or a pat).
- MATCH THE PICTURES: narration may only mention people, animals, places and objects that are ON SCREEN in that scene
  (from the menus below). No benches, crowds, "her friends" or "everyone" unless those characters are shown.
  If the story needs friends, put them on screen as cast characters (use 2-3 characters for most stories).
  Don't describe colours or details the cartoon can't show (the puppy is light brown).
- Speech bubbles must fit that exact moment and mood (a sad character doesn't say "Join the fun!").
- Before answering, check: clear feeling? does the character change? would a parent feel something at the end?
  is it clearly different from the recent stories? does every sentence match what is on screen and make sense?
  If not, rewrite it.

- {n} story scenes. The cartoon can ONLY show what these menus allow, so build the story from them:
  backgrounds: home (room with window and low table), park, night (moon and stars), village (huts, dirt road),
               school (classroom with blackboard and a low table), jungle (big trees)
  actions: idle, bounce (happy hopping), walk (moves to another place), jump (big happy jump), wave, point,
           hero (hands on hips, proud), droop (sad, arms down)
  moods: happy, smile, sad, surprised, cross
  props: plate (state: one / two / three / empty = laddoos on a plate), bird, ball, puppy, kitten, tree_mango, mango,
         gift, heart, flower_pot (state: fresh / wilted), book, kite
  prop places: table (home or school only), window (home only), ground_left, ground_centre, ground_right, sky
  prop motion (optional): hop, bob, sway, float, arrive (comes in from the side)
  character places: left, centre_left, centre, centre_right, right

Return JSON only:
{{
  "plan": {{"feeling": "the one feeling the story is about", "wish_or_worry": "...", "quirk": "...",
            "turning_point": "what the character chooses to do", "repeat_line": "the say-along line"}},
  "title": "3-5 word catchy title that makes people curious",
  "cast": ["ids of the characters in this story"],
  "moral_line": "the lesson in at most 6 simple words",
  "question": "one short question for parents about their own child and this feeling",
  "music": "playful" or "gentle" or "adventure",
  "caption": "1 hook line with 1-2 emoji, blank line, a question for parents, blank line, 'A new story every day ✨ Follow @kahani.time.kids', blank line, 8 hashtags ending with #kahanitimekids",
  "scenes": [
    {{"bg": "...",
      "narration": "what the storyteller says: 1-2 very simple sentences, 8-20 words; call characters by name",
      "chars": [{{"who": "id", "place": "...", "action": "...", "mood": "...", "walk_to": "(only if action is walk) another place"}}],
      "props": [{{"kind": "...", "state": "(optional)", "place": "...", "motion": "(optional)"}}],
      "say": [{{"who": "a character id or prop", "text": "max 4 words, no emoji"}}],
      "sparkle": false}}
  ]
}}
At most 3 characters and 2 props per scene, at most 2 speech bubbles. Give characters different places.
Make actions change from scene to scene so the cartoon feels alive (walk, jump, wave, point...).
"""

BGS = ("home", "park", "night", "village", "school", "jungle")
PLACES_X = {"left": 260, "centre_left": 390, "centre": 540, "centre_right": 690, "right": 820}
PROP_PLACES = {"table": (540, 1160), "window": (790, 715), "ground_left": (150, 1340), "ground_centre": (540, 1340),
               "ground_right": (930, 1340), "sky": (540, 640)}
MAX_PROP_W = {"tree_mango": 1}


def write(moral, recent_titles, n=5, recent_cast=(), idea=None):
    cast = "\n".join(f"  {k}: {v['name']} - {v['desc']}" for k, v in CAST.items())
    if idea:
        names = ", ".join(idea["cast"])
        beats = "\n".join(f"  {i+1}. {b}" for i, b in enumerate(idea["beats"]))
        source = (f'TELL THIS STORY (from our hand-picked story bank): "{idea["title"]}" - moral: {idea["moral"]}.\n'
                  f"Use exactly these characters: {names}. Main background: {idea['bg']}.\n"
                  f"Keep every event, in this order, one scene per beat ({len(idea['beats'])} scenes). "
                  f"Keep the title. Make the narration warm and vivid; never change what happens.\n{beats}")
        n = len(idea["beats"])
    else:
        source = "Write ONE new, original story."
    prompt = PROMPT.format(moral=moral, n=n, recent=", ".join(recent_titles[-30:]) or "none yet", cast=cast,
                           recent_cast=", ".join(recent_cast) or "none", source=source)
    last = []
    for _ in range(3):
        s = gemini_api.generate_json(prompt)
        last = check(s, n)
        if not last:
            if idea:
                s["title"] = idea["title"]; s["moral_line"] = idea["moral_line"]
                s["cast"] = [c for c in idea["cast"] if c in CAST]
            return s
        print("  story rejected:", "; ".join(last))
    raise gemini_api.ApiError("Could not get a valid cartoon story: " + "; ".join(last))


def check(s, n):
    errs = [f"missing {k}" for k in ("title", "moral_line", "question", "caption", "scenes") if not s.get(k)]
    sc = s.get("scenes") or []
    if not (n - 1 <= len(sc) <= n + 1): errs.append(f"{len(sc)} scenes")
    used = {c.get("who") for x in sc for c in (x.get("chars") or []) if c.get("who") in CAST}
    if not used: errs.append("no known characters on screen")
    for i, x in enumerate(sc):
        w = len(str(x.get("narration", "")).split())
        if not 4 <= w <= 26: errs.append(f"scene {i+1} narration {w} words")
    return errs


def _place_chars(chars):
    """Turn the model's character choices into positions; keep everyone apart and inside the frame."""
    out, taken = [], []
    slots = [260, 540, 820] if len(chars) >= 3 else [270, 810]
    for c in chars[:3]:
        if c.get("who") not in CAST: continue
        x = PLACES_X.get(c.get("place"), slots[len(out) % len(slots)])
        if any(abs(x - t) < 230 for t in taken):
            x = next((sx for sx in slots + [540, 390, 690] if all(abs(sx - t) >= 230 for t in taken)), x)
        act = c.get("action") if c.get("action") in ACTS else "idle"
        mood = c.get("mood") if c.get("mood") in MOODS else "smile"
        o = {"who": c["who"], "x": x, "act": act, "mood": mood}
        if act == "walk":
            to = PLACES_X.get(c.get("walk_to"), 540)
            if abs(to - x) < 150 or any(abs(to - t) < 200 for t in taken):
                o["act"] = "bounce"
            else:
                o.update(from_x=x, to_x=to, x=to, face="right" if to > x else "left")
        taken.append(o["x"]); out.append(o)
    return out


def stage(story, durations, story_no):
    """Convert the model's menu choices into an engine spec. durations: seconds per story scene (from the voice)."""
    scenes = [{"type": "title", "bg": "park", "dur": 3.0}]
    for i, (sc, dur) in enumerate(zip(story["scenes"], durations)):
        bg = sc.get("bg") if sc.get("bg") in BGS else "park"
        chars = _place_chars(sc.get("chars") or [])
        props = []
        for p in (sc.get("props") or [])[:2]:
            kind = p.get("kind")
            if kind not in PROPS: continue
            place = p.get("place", "ground_centre")
            if (place == "window" and bg != "home") or (place == "table" and bg not in ("home", "school")): place = "ground_centre"
            if kind == "kite": place = "sky"
            x, y = PROP_PLACES.get(place, PROP_PLACES["ground_centre"])
            if place == "ground_centre" and any(abs(c["x"] - 540) < 160 for c in chars): y = 1380
            q = {"kind": kind, "x": x, "y": y, "layer": "front" if place.startswith("ground") else "back"}
            if p.get("state"): q["state"] = str(p["state"])
            m = p.get("motion")
            if m in ("hop", "bob", "sway", "float"): q["anim"] = m
            if m == "arrive": q.update(from_x=1200 if x > 540 else -150, from_y=y, move=1.2)
            if kind in ("bird",) and x > 540: q["flip"] = True
            props.append(q)
        say = []
        for j, b in enumerate((sc.get("say") or [])[:2]):
            txt = " ".join(str(b.get("text", "")).split()[:5])
            if not txt or any(ord(ch) > 0x2FFF for ch in txt): continue
            who = b.get("who")
            item = {"text": txt, "at": 0.3 + j * 1.4}
            if who in [c["who"] for c in chars]: item["who"] = who
            else:
                src = next((p for p in props if p["kind"] in ("bird", "puppy", "kitten")), props[0] if props else None)
                item.update(x=src["x"] if src else 540, y=(src["y"] - 150) if src else 700)
            say.append(item)
        scenes.append({"type": "story", "bg": bg, "dur": round(dur, 2), "text": sc["narration"].strip(),
                       "chars": chars, "props": props, "say": say, "sparkle": bool(sc.get("sparkle")) or i == len(story["scenes"]) - 1,
                       "lead": 0.3})
    cast = [c for c in (story.get("cast") or []) if c in CAST]
    for sc_ in scenes:
        for c in sc_.get("chars", []):
            if c["who"] not in cast: cast.append(c["who"])
    return {"title": story["title"], "story_no": story_no, "cast": cast[:3], "scenes": scenes}


def add_moral(spec, story, dur):
    spec["scenes"].append({"type": "moral", "bg": "park", "dur": round(dur, 2), "text": story["moral_line"],
                           "question": story["question"]})
    return spec


def next_idea(history, bank_path):
    """Next story from content/story_bank.json that hasn't been told yet (None when the bank is used up)."""
    import json, os
    if not os.path.exists(bank_path): return None
    used = {h.get("idea") for h in history} | {h.get("title") for h in history}
    left = [i for i in json.load(open(bank_path, encoding="utf-8")) if i["id"] not in used and i["title"] not in used]
    recent_morals = {h.get("moral") for h in history[-5:]}
    # never repeat a lesson that was taught in the last 5 stories, if any other story is left
    return next((i for i in left if i["moral"] not in recent_morals), left[0] if left else None)
