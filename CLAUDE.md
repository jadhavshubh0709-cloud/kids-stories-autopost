# Twin Heroes AI story factory (@twin.heros)

Faceless kids' story page: one short 3D-animated moral story per day starring original twin heroes
**Veer** (boy, blue suit, red cape) and **Veera** (girl, pink suit, yellow cape). Owner: Shubhangi.
Audience: parents of 3-8 year olds in India. Simple English, Indian setting.

## Pipeline (fully automatic, runs on GitHub Actions)
1. `make-story.yml` (9 AM IST daily) runs `pipeline/make_story_reel.py`:
   story (Gemini text, JSON) -> 5 clips of 8 s (Gemini Omni Flash video, with `assets/characters/*.png` as references)
   -> narrator voice per scene (Gemini TTS) -> `pipeline/assemble.py` adds title, subtitles, moral card, music -> `reels/<date>/`.
2. `post-reel.yml` (7 PM IST) posts `reels/<today>/reel.mp4` + `caption.txt` to Instagram.
- One secret for AI: `GEMINI_API_KEY`. Model names are env vars in `pipeline/gemini_api.py` (change there if Google renames models).
- Offline test without API calls: `MOCK_GEMINI=1 python3 pipeline/make_story_reel.py --date 2000-01-01` (delete the output after).
- `content/history.json` keeps used titles/morals so stories don't repeat.

## Rules
- Don't edit `src/`, secrets, or run `post-reel.yml` unless the owner asks.
- Stories must stay gentle: no villains, danger, punishment, brands, real people; adults are never shown on screen.
- Never print or commit API keys or tokens.
