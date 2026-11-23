"""Writes one original Twin Heroes story as JSON using the Gemini text model."""
import json
import gemini_api

CHARACTERS = (
    "Veer and Veera, 6-year-old Indian twin siblings who are little superheroes. "
    "Veer: boy, short spiky black hair, blue superhero suit, red cape, small blue eye mask, yellow star on chest. "
    "Veera: girl, two black ponytails with yellow bows, pink superhero suit, yellow cape, pink eye mask, blue star on chest."
)

STYLE = ("3D animated cartoon in a cute, high-quality family-movie style: stylized characters with big friendly eyes, "
         "soft rounded shapes, bright warm colours, soft cinematic lighting, gentle camera movement. "
         "Vertical 9:16 framing with the characters in the upper two-thirds of the frame. "
         "No text, no captions, no logos, no speech or singing; only soft ambient sounds that fit the scene.")

MORALS = ["sharing", "honesty", "kindness to animals", "helping elders", "saying sorry", "courage", "patience",
          "keeping things clean", "gratitude", "teamwork", "not giving up", "listening to parents", "caring for plants and nature",
          "being a good friend", "telling the truth even when it is hard", "helping someone who is new", "saving water"]

PROMPT = """You write very short animated moral stories for an Instagram page for parents of 3-8 year old children in India.
Main characters (they appear in EVERY scene): {characters}

Write ONE new, original story.
- Moral to teach: {moral}
- Setting: everyday Indian life (home, park, school, market, village, festival, garden). Adults (Maa, Papa, Dadi) can be
  mentioned in narration but must NOT appear on screen. Animals may appear.
- Gentle and kind: no villains, violence, danger, punishment, scary moments, brands or real people. Ends happily.
- Do not retell these recent stories: {recent}
- Exactly {n} scenes. Each scene is ONE continuous 8-second animated shot.

Return JSON only, with this exact shape:
{{
  "title": "3-5 word catchy title",
  "moral": "{moral}",
  "moral_line": "the lesson in at most 6 simple words, e.g. Sharing makes happiness bigger!",
  "question": "one short question for parents to answer in the comments",
  "music": "playful" or "gentle" or "adventure",
  "caption": "Instagram caption: 1 hook line with 1-2 emoji, blank line, a question for parents, blank line, 'A new Twin Heroes story every day ✨ Follow @twin.heros', blank line, 8 hashtags ending with #twinheros",
  "scenes": [
    {{"visual": "what the camera shows in this 8-second shot: where they are, what Veer and Veera DO, facial expressions, any animal or object, camera move. 40-70 words. Describe the twins by name AND appearance.",
      "sound": "ambient sounds only, e.g. birds chirping, soft wind",
      "narration": "what the storyteller says over this shot: 1-2 very simple sentences, 8-18 words, present or past tense"}}
  ]
}}
"""


def write_story(moral, recent_titles, n_scenes=5):
    prompt = PROMPT.format(characters=CHARACTERS, moral=moral, n=n_scenes,
                           recent=", ".join(recent_titles[-30:]) or "none yet")
    for attempt in range(3):
        story = gemini_api.generate_json(prompt)
        errs = validate(story, n_scenes)
        if not errs:
            return story
        print("  story rejected:", "; ".join(errs))
    raise gemini_api.ApiError("Could not get a valid story after 3 tries: " + "; ".join(errs))


def validate(s, n):
    errs = []
    for k in ("title", "moral_line", "question", "caption", "scenes"):
        if not s.get(k): errs.append(f"missing {k}")
    if s.get("music") not in ("playful", "gentle", "adventure"): s["music"] = "playful"
    sc = s.get("scenes") or []
    if len(sc) != n: errs.append(f"{len(sc)} scenes instead of {n}")
    for i, x in enumerate(sc):
        w = len(str(x.get("narration", "")).split())
        if not 4 <= w <= 24: errs.append(f"scene {i+1} narration has {w} words")
        if len(str(x.get("visual", "")).split()) < 15: errs.append(f"scene {i+1} visual too short")
    if "#twinheros" not in s.get("caption", ""): s["caption"] = s.get("caption", "").rstrip() + " #twinheros"
    return errs


def video_prompt(scene):
    return (f"{STYLE}\nCharacters (match the reference images exactly): {CHARACTERS}\n"
            f"Shot: {scene['visual']}\nSound: {scene.get('sound', 'soft ambient sounds')}. No dialogue.")
