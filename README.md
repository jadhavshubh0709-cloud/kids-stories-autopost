# kids-stories-autopost: free daily AI story reels for @twin.heros

Every day, automatically and **free**:
- **9 AM IST**: AI writes a new moral story starring Veer and Veera. It makes a 3D-style picture for each scene
  with slow camera movement, records a narrator voice, and builds a 30-45 s reel with title, subtitles, music and a "story lesson" ending.
  It is saved in `reels/<date>/`.
- **7 PM IST**: the reel is posted to Instagram.

You have until 7 PM to watch it on GitHub. To skip a day, delete that day's folder in `reels/`.

## Free services used
| Part | Service | Cost |
|---|---|---|
| Story + narrator voice | Google Gemini API, free tier (key **without** billing) | Free |
| Scene pictures | Cloudflare Workers AI, free plan (10,000 neurons/day; about 600 are used per day) | Free, no card |
| Building, hosting, posting | GitHub Actions + Pages, Instagram API | Free |

If Cloudflare isn't set up, the pictures come from Pollinations instead. That's free too, but slower.

## One-time setup (about 15 minutes)
1. **Gemini key**: go to aistudio.google.com → **Get API key** → **Create API key**. Don't turn on billing; then you can never be charged.
2. **Cloudflare**: sign up free at dash.cloudflare.com (no card needed).
   - Copy your **Account ID**. It's in the browser address bar after you log in, or under Workers & Pages → Overview.
   - Go to My Profile → **API Tokens** → Create Token → use the **Workers AI** template → Create. Copy the token.
3. In this repo, go to **Settings → Secrets and variables → Actions** and add these secrets:
   - `GEMINI_API_KEY`
   - `CF_ACCOUNT_ID`
   - `CF_API_TOKEN`
   - `IG_ACCESS_TOKEN` (the same Instagram posting token used for @smartwork.ai.in)
4. **Settings → Pages**: deploy from branch `main`, folder `/ (root)`.
5. **Actions → Make daily story reel → Run workflow** to make today's reel and check it.

## Optional: real AI video (paid)
Add the repo variable `VIDEO_MODE` = `ai` and turn on billing for the Gemini key. Clips then come from Gemini Omni Flash
(roughly ₹350 per reel). Run **Make character designs (one time)** first so the twins look the same in every clip.

## Files
```
pipeline/make_story_reel.py   main script (story -> pictures/clips -> voice -> reel)
pipeline/images_api.py        free scene pictures (Cloudflare FLUX, Pollinations fallback)
pipeline/gemini_api.py        Gemini API: story text, voice, and the paid video/image options
pipeline/story_writer.py      story prompt, characters, picture/video style
pipeline/assemble.py          ffmpeg + Pillow: camera moves, subtitles, title, moral card, music
tools/make_music.py           original background music (music/*.m4a)
src/PostReel.java             Instagram poster
```
Fonts: Poppins (SIL Open Font License). Music is synthesized in code, so there are no copyright issues.
