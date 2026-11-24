"""FREE scene pictures for the 'stills' mode (default).

1st choice: Cloudflare Workers AI, FLUX.1 schnell. Free plan = 10,000 neurons/day, no credit card;
            one picture uses roughly 100 neurons, so ~6 pictures a day is far inside the free limit.
            Secrets: CF_ACCOUNT_ID, CF_API_TOKEN (token with "Workers AI" permission).
Fallback:   Pollinations (image.pollinations.ai), free without any account; slower and rate-limited.
MOCK_GEMINI=1 makes placeholder pictures offline.
"""
import base64, json, os, subprocess, time, urllib.error, urllib.parse, urllib.request

CF_MODEL = os.environ.get("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")


class ImageError(RuntimeError):
    pass


def _cloudflare(prompt, seed, out):
    acct, tok = os.environ.get("CF_ACCOUNT_ID"), os.environ.get("CF_API_TOKEN")
    if not (acct and tok):
        raise ImageError("Cloudflare secrets CF_ACCOUNT_ID / CF_API_TOKEN not set")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{CF_MODEL}"
    body = json.dumps({"prompt": prompt[:2000], "steps": 8, "seed": int(seed)}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read(); ctype = r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raise ImageError(f"Cloudflare HTTP {e.code}: {e.read().decode(errors='replace')[:400]}") from None
    if ctype.startswith("image/"):
        open(out, "wb").write(raw); return out
    data = json.loads(raw)
    img = (data.get("result") or {}).get("image") or data.get("image")
    if not img:
        raise ImageError(f"Cloudflare returned no image: {json.dumps(data)[:400]}")
    open(out, "wb").write(base64.b64decode(img)); return out


def _pollinations(prompt, seed, out):
    q = urllib.parse.quote(prompt[:1500])
    url = f"https://image.pollinations.ai/prompt/{q}?width=1080&height=1920&model=flux&nologo=true&seed={int(seed)}"
    req = urllib.request.Request(url, headers={"User-Agent": "twin-heroes-bot"})
    with urllib.request.urlopen(req, timeout=240) as r:
        raw = r.read()
        if not r.headers.get("Content-Type", "").startswith("image/"):
            raise ImageError("Pollinations returned no image")
    open(out, "wb").write(raw); return out


def generate_still(prompt, out, seed):
    if os.environ.get("MOCK_GEMINI") == "1":
        col = ["0xf4a261", "0x2a9d8f", "0xe76f51", "0x8ab17d", "0x6d597a", "0x457b9d"][seed % 6]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc2=s=1024x1024",
                        "-vf", f"drawbox=x=0:y=0:w=1024:h=1024:color={col}@0.6:t=fill", "-frames:v", "1", out], check=True)
        return out
    errors = []
    for name, fn in (("cloudflare", _cloudflare), ("pollinations", _pollinations)):
        for attempt in range(3):
            try:
                return fn(prompt, seed, out)
            except Exception as e:
                errors.append(f"{name}: {str(e)[:200]}")
                if "not set" in str(e): break
                time.sleep(15 * (attempt + 1))
    raise ImageError("Could not make a picture. " + " | ".join(errors[-4:]))
