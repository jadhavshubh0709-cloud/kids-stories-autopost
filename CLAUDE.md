# Kahani Time story factory (@kahani.time.kids, formerly @twin.heros)

Faceless kids' story page: one short animated moral story per day. Owner: Shubhangi.
Owner does NOT want every story about the twins: each story picks 1-3 characters from a varied cast in
`cartoon_engine.CAST` (kids Aarav, Meera, Anya; hero twins Veer & Veera; animals Gappu elephant, Chiku bunny,
Bandu monkey, Tara bear cub), avoiding the cast of recent stories. Backgrounds: home, park, night, village, school, jungle.
Audience: parents of 3-8 year olds in India. Simple English, Indian setting. Caption hashtag ends with #kahanitimekids.

## Pipeline (fully automatic, runs on GitHub Actions)
1. `make-story.yml` (9 AM IST daily) runs `pipeline/make_story_reel.py`:
   DEFAULT `VIDEO_MODE=cartoon` (owner chose this, FREE): Gemini (free tier) writes the story AND stages each scene from
   menus (`pipeline/cartoon_writer.py`) -> `pipeline/cartoon_engine.py` animates Veer & Veera (walk, jump, wave...) ->
   Gemini TTS narrator (free tier) -> `assemble.mix_voices` adds voice + music -> `reels/<date>/`.
   Other modes: `stills` (free AI pictures + camera pans, Cloudflare), `ai` (paid Gemini Omni Flash video). Keep it free.
2. `post-reel.yml` (7 PM IST) posts `reels/<today>/reel.mp4` + `caption.txt` to Instagram.
- Secrets: `GEMINI_API_KEY` (no billing), `CF_ACCOUNT_ID`, `CF_API_TOKEN`, `IG_ACCESS_TOKEN`. Model names are env vars in `pipeline/gemini_api.py` (change there if Google renames models).
- Offline test without API calls: `MOCK_GEMINI=1 python3 pipeline/make_story_reel.py --date 2000-01-01` (delete the output after).
- `content/story_bank.json`: owner wants GOOD stories with a clear moral, so cartoon mode tells the next untold story from
  this hand-written bank (AI only polishes words + stages scenes). When the bank runs out it falls back to AI-invented stories:
  add more entries before that. Narration must only mention what is on screen.
- `content/history.json` keeps used titles/morals (and bank `idea` ids) so stories don't repeat.

## Rules
- Don't edit `src/`, secrets, or run `post-reel.yml` unless the owner asks.
- Stories must stay gentle: no villains, danger, punishment, brands, real people; adults are never shown on screen.
- Never print or commit API keys or tokens.
