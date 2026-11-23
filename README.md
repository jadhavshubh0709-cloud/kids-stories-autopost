# kids-stories-autopost: daily AI 3D story reels for @twin.heros

Every day, with no manual work:
- **9 AM IST**: AI writes a new moral story, makes 5 animated 3D clips of Veer and Veera, records a narrator voice,
  and builds a finished 30-45 s reel (title, read-along subtitles, music, "story lesson" ending). It is saved in `reels/<date>/`.
- **7 PM IST**: the reel is posted to Instagram.

You have until 7 PM to watch it on GitHub. To skip a day, delete that day's folder in `reels/`.

## One-time setup
1. **Gemini API key**: open Google AI Studio (aistudio.google.com), click **Get API key**, then **Create API key**.
   Video generation needs a paid key, so turn on billing for that project in AI Studio.
   Set a monthly **budget alert** in Google Cloud Billing.
2. In this repo, go to **Settings → Secrets and variables → Actions** and add:
   - `GEMINI_API_KEY`: the key from step 1
   - `IG_ACCESS_TOKEN`: the same Instagram posting token used for @smartwork.ai.in
3. **Settings → Pages**: deploy from branch `main`, folder `/ (root)`.
4. **Actions → Make character designs (one time) → Run workflow**. Then open `assets/characters/` and check the twins.
   If you don't like them, delete the images and run it again.
5. **Actions → Make daily story reel (AI) → Run workflow** to make the first reel now and check it.

## Cost control
- Repo **Variables** (Settings → Secrets and variables → Actions → Variables): `SCENES` (default 5; 4 is cheaper)
  and `RESOLUTION` (default `720p`).
- To post every other day, change the cron line in `.github/workflows/make-story.yml` to `"30 3 */2 * *"`.

## Files
```
pipeline/make_story_reel.py   main script (story -> clips -> voice -> reel)
pipeline/gemini_api.py        Gemini API calls (text, image, video, speech), stdlib only
pipeline/story_writer.py      story prompt, characters, style
pipeline/assemble.py          ffmpeg + Pillow: subtitles, title, moral card, music, final mix
pipeline/make_characters.py   one-time character reference images
tools/make_music.py           original background music (music/*.m4a)
src/PostReel.java             Instagram poster
```
Fonts: Poppins (SIL Open Font License). Music is synthesized in code, so there are no copyright issues.
