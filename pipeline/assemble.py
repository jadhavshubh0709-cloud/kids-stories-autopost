"""Puts AI clips + narrator voice + subtitles + title + moral card + music together into one 1080x1920 reel."""
import json, os, subprocess, textwrap
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
FONT_DIR = os.path.join(ROOT, "assets", "fonts")
INK = (52, 36, 60)
YELLOW = (255, 200, 40)
HANDLE = "@twin.heros"
INTRO = 2.6        # seconds of title over the first clip (cover frame is taken at 2.0 s)


def font(size, w="Bold"): return ImageFont.truetype(os.path.join(FONT_DIR, f"Poppins-{w}.ttf"), size)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + " ".join(cmd)[:400] + "\n" + r.stderr[-1500:])
    return r.stdout


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).strip())


def has_audio(path):
    return "audio" in run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", path])


def wrap(d, text, f, maxw):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: out.append(cur); cur = w
    if cur: out.append(cur)
    return out


def outlined(d, xy, text, f, fill, sw=8):
    d.text(xy, text, font=f, fill=fill, stroke_width=sw, stroke_fill=INK)


def pill(d, label, y=150):
    f = font(36); tw = d.textlength(label, font=f)
    d.rounded_rectangle([(W - tw) / 2 - 32, y, (W + tw) / 2 + 32, y + 72], 36, fill=YELLOW)
    d.text(((W - tw) / 2, y + 10), label, font=f, fill=INK)


# ------------------------------------------------------------------ overlay images
def subtitle_png(text, story_no, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    pill(d, f"STORY #{story_no}")
    f = font(54); lines = wrap(d, text, f, 900)
    if len(lines) > 3: f = font(46); lines = wrap(d, text, f, 920)
    lh = int(f.size * 1.32); bh = lh * len(lines) + 64; y0 = 1440
    d.rounded_rectangle([50, y0, W - 50, y0 + bh], 44, fill=(255, 255, 255, 235), outline=YELLOW, width=8)
    y = y0 + 32
    for ln in lines:
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=INK); y += lh
    img.save(path)


def title_png(title, story_no, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 760], fill=(0, 0, 0, 0))
    shade = Image.new("RGBA", (W, 820), (0, 0, 0, 0)); sd = ImageDraw.Draw(shade)
    for y in range(820): sd.line([(0, y), (W, y)], fill=(20, 10, 40, int(150 * (1 - y / 820))))
    img.alpha_composite(shade)
    pill(d, f"STORY #{story_no}")
    f1 = font(130); t = "TWIN HEROES"; outlined(d, ((W - d.textlength(t, font=f1)) / 2, 270), t, f1, (255, 210, 50), 10)
    f2 = font(84); y = 450
    for ln in wrap(d, title, f2, 960):
        outlined(d, ((W - d.textlength(ln, font=f2)) / 2, y), ln, f2, (255, 255, 255), 8); y += 104
    img.save(path)


def moral_png(bg_frame, story, path):
    bg = Image.open(bg_frame).convert("RGB").resize((W, H)).filter(ImageFilter.GaussianBlur(14)).convert("RGBA")
    bg.alpha_composite(Image.new("RGBA", (W, H), (40, 20, 70, 160)))
    d = ImageDraw.Draw(bg)
    f0 = font(58); lab = "STORY LESSON"; outlined(d, ((W - d.textlength(lab, font=f0)) / 2, 330), lab, f0, (255, 210, 50), 6)
    f1 = font(92); y = 450
    for ln in wrap(d, story["moral_line"], f1, 940):
        outlined(d, ((W - d.textlength(ln, font=f1)) / 2, y), ln, f1, (255, 255, 255), 8); y += 116
    f2 = font(48); q = wrap(d, story["question"], f2, 860); bh = len(q) * 64 + 64; y = max(y + 80, 1000)
    d.rounded_rectangle([70, y, W - 70, y + bh], 40, fill=YELLOW); yy = y + 32
    for ln in q:
        d.text(((W - d.textlength(ln, font=f2)) / 2, yy), ln, font=f2, fill=INK); yy += 64
    f3 = font(46, "Medium"); fl = f"Follow {HANDLE} for daily stories"
    outlined(d, ((W - d.textlength(fl, font=f3)) / 2, 1560), fl, f3, (255, 255, 255), 4)
    bg.convert("RGB").save(path)


# ------------------------------------------------------------------ scene rendering
VIDEO_OUT = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]


def render_scene(clip, voice, subtitle, out, intro_png=None, story_no=1):
    """Clip scaled to 1080x1920; narration starts after the intro (scene 1) or 0.3 s; clip's own sound kept quietly."""
    start = INTRO if intro_png else 0.3
    vlen = duration(voice)
    D = round(start + vlen + 0.7, 2)
    inputs = ["-i", clip, "-i", voice, "-loop", "1", "-i", subtitle]
    if intro_png: inputs += ["-loop", "1", "-i", intro_png]
    if not has_audio(clip): inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    amb = "0:a" if has_audio(clip) else f"{4 if intro_png else 3}:a"
    v = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
         f"tpad=stop_mode=clone:stop_duration=30,trim=duration={D},setpts=PTS-STARTPTS[bg];"
         f"[bg][2:v]overlay=0:0:enable='gte(t,{start - 0.1})'[v1]")
    if intro_png:
        v += f";[v1][3:v]overlay=0:0:enable='lt(t,{INTRO})'[v]"
    else:
        v += ";[v1]null[v]"
    ms = int(start * 1000)
    a = (f";[{amb}]aresample=48000,volume=0.35,apad,atrim=0:{D}[amb];"
         f"[1:a]aresample=48000,adelay={ms}|{ms},apad,atrim=0:{D}[nar];"
         f"[amb][nar]amix=inputs=2:normalize=0,aformat=channel_layouts=stereo[a]")
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", v + a, "-map", "[v]", "-map", "[a]",
         "-t", str(D), *VIDEO_OUT, out])
    return D


def render_moral(last_clip, voice, story, work, out):
    frame = os.path.join(work, "last_frame.jpg")
    run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.2", "-i", last_clip, "-frames:v", "1", "-update", "1", frame])
    card = os.path.join(work, "moral.png"); moral_png(frame, story, card)
    D = round(max(4.5, duration(voice) + 1.2), 2)
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", card, "-i", voice,
         "-filter_complex", f"[0:v]fps={FPS},trim=duration={D},format=yuv420p[v];[1:a]aresample=48000,adelay=400|400,apad,atrim=0:{D},aformat=channel_layouts=stereo[a]",
         "-map", "[v]", "-map", "[a]", "-t", str(D), *VIDEO_OUT, out])
    return D


def build_reel(story, clips, voices, moral_voice, work, out_mp4, music_path):
    os.makedirs(work, exist_ok=True)
    parts, total = [], 0.0
    for i, (sc, clip, voice) in enumerate(zip(story["scenes"], clips, voices)):
        sub = os.path.join(work, f"sub{i}.png"); subtitle_png(sc["narration"], story["story_no"], sub)
        intro = None
        if i == 0:
            intro = os.path.join(work, "title.png"); title_png(story["title"], story["story_no"], intro)
        p = os.path.join(work, f"part{i}.mp4"); total += render_scene(clip, voice, sub, p, intro); parts.append(p)
    p = os.path.join(work, "part_moral.mp4"); total += render_moral(clips[-1], moral_voice, story, work, p); parts.append(p)
    lst = os.path.join(work, "parts.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(x)}'\n" for x in parts))
    joined = os.path.join(work, "joined.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    total = duration(joined)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", joined, "-stream_loop", "-1", "-i", music_path,
         "-filter_complex", f"[1:a]volume=0.16,afade=t=out:st={max(0, total - 1.5)}:d=1.5[m];"
                            f"[0:a][m]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", str(total),
         "-movflags", "+faststart", out_mp4])
    return total


def still_to_clip(img, out, direction=0, dur=12.0):
    """Free 'moving storybook' shot: slow camera pan across an AI picture (any size) to fill 1080x1920."""
    iw, ih = Image.open(img).size
    s = max(W / iw, H / ih) * 1.12
    sw, sh = int(iw * s) // 2 * 2, int(ih * s) // 2 * 2
    ex, ey = sw - W, sh - H                       # how far the camera can travel
    p = f"(t/{dur})"
    if direction % 4 == 0:   x, y = f"{ex}*(0.3+0.4*{p})", f"{ey}/2"          # pan right
    elif direction % 4 == 1: x, y = f"{ex}*(0.7-0.4*{p})", f"{ey}/2"          # pan left
    elif direction % 4 == 2: x, y = f"{ex}/2", f"{ey}*(0.9-0.8*{p})"           # tilt up
    else:                    x, y = f"{ex}*(0.35+0.3*{p})", f"{ey}*(0.3+0.4*{p})"  # diagonal
    big = out + ".big.png"                        # pre-scale once (2x) so every frame is just a smooth crop
    Image.open(img).convert("RGB").resize((sw * 2, sh * 2), Image.LANCZOS).save(big)
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", big,
         "-vf", f"crop={W * 2}:{H * 2}:x='2*({x})':y='2*({y})',scale={W}:{H}:flags=bicubic,fps={FPS},format=yuv420p",
         "-t", str(dur), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out])
    os.remove(big)
    return out


def mix_voices(silent_video, voices, music_path, out_mp4):
    """voices: list of (wav_path, start_seconds). Narration on top, background music quietly underneath."""
    total = duration(silent_video)
    inputs = ["-i", silent_video, "-stream_loop", "-1", "-i", music_path]
    parts = []
    for k, (wav, start) in enumerate(voices):
        inputs += ["-i", wav]; ms = int(start * 1000)
        parts.append(f"[{k + 2}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{k}]")
    mixv = "".join(f"[v{k}]" for k in range(len(voices)))
    fc = ";".join(parts) + (f";{mixv}amix=inputs={len(voices)}:normalize=0[nar];" if voices else "") + \
         f"[1:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.18,atrim=0:{total},afade=t=out:st={max(0, total - 1.5)}:d=1.5[m];" + \
         (f"[nar][m]amix=inputs=2:normalize=0:duration=longest," if voices else "[m]") + f"loudnorm=I=-16:TP=-1.5,atrim=0:{total}[a]"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", str(total), "-movflags", "+faststart", out_mp4])
    return total



def split_by_pauses(src, n, work, weights=None):
    """Split one narration recording into n lines. For each line break we look for the longest pause NEAR where
    that line should end (estimated from its word count), so pauses inside a sentence don't confuse the split.
    Returns [(wav_path, length_seconds)]."""
    import array, wave
    with wave.open(src) as w:
        rate, ch, frames = w.getframerate(), w.getnchannels(), w.getnframes()
        pcm = array.array("h", w.readframes(frames))
    mono = pcm[::ch]; step = int(0.02 * rate)
    energy = [max((abs(v) for v in mono[i:i + step]), default=0) for i in range(0, len(mono), step)]
    peak = max(energy) or 1; thr = peak * 0.05
    runs, start = [], None                                   # silent stretches: (start_s, end_s)
    for k, e in enumerate(energy + [peak]):
        if e < thr and start is None: start = k
        elif e >= thr and start is not None:
            if start > 0 and k < len(energy) and (k - start) >= 6: runs.append((start * 0.02, k * 0.02))
            start = None
    total = len(mono) / rate
    # trim leading/trailing silence from the estimate
    voiced = [k for k, e in enumerate(energy) if e >= thr]
    t0, t1 = (voiced[0] * 0.02, voiced[-1] * 0.02 + 0.02) if voiced else (0, total)
    weights = weights or [1] * n
    cum, acc = [], 0
    for w_ in weights[:-1]:
        acc += w_; cum.append(t0 + (t1 - t0) * acc / sum(weights))
    window = (t1 - t0) / n * 0.45
    cuts, prev = [], t0
    for e in cum:
        cands = [(b - a, (a + b) / 2) for a, b in runs if (a + b) / 2 > prev + 0.5 and abs((a + b) / 2 - e) <= window]
        if cands:
            mid = max(cands, key=lambda c: c[0] - 0.15 * abs(c[1] - e))[1]
        else:
            mid = max(e, prev + 0.5)
        cuts.append(mid); prev = mid
    edges = [0.0] + cuts + [total]
    out = []
    for i in range(n):
        seg = os.path.join(work, f"line{i}.wav")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ss", f"{edges[i]:.3f}", "-to", f"{edges[i + 1]:.3f}",
             "-af", "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse", seg])
        out.append((seg, duration(seg)))
    print("  narration split at:", ", ".join(f"{c:.1f}s" for c in cuts), f"(total {total:.1f}s)", flush=True)
    return out
