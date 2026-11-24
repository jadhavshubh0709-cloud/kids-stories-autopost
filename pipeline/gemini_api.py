"""Thin client for the Google Gemini API (stdlib only, so it runs anywhere).

Used services (one API key: secret GEMINI_API_KEY):
  - story writing  : TEXT_MODEL   (default gemini-3.5-flash)          generateContent, JSON output
  - character art  : IMAGE_MODEL  (default gemini-3.1-flash-image)    generateContent, image output
  - 3D video clips : VIDEO_MODEL  (default gemini-omni-1.1-flash)     Interactions API, video output
  - narrator voice : TTS_MODEL    (default gemini-3.1-flash-tts-preview) generateContent, audio output

Model names can be changed with environment variables without touching code.
Set MOCK_GEMINI=1 to run the whole pipeline offline with placeholder media (for testing).
"""
import base64, json, os, struct, subprocess, sys, time, urllib.error, urllib.request

BASE = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
TEXT_MODEL = os.environ.get("TEXT_MODEL", "gemini-3.5-flash")
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gemini-3.1-flash-image")
VIDEO_MODEL = os.environ.get("VIDEO_MODEL", "gemini-omni-1.1-flash")
TTS_MODEL = os.environ.get("TTS_MODEL", "gemini-3.1-flash-tts-preview")
VOICE = os.environ.get("TTS_VOICE", "Kore")
MOCK = os.environ.get("MOCK_GEMINI") == "1"


class ApiError(RuntimeError):
    pass


def _key():
    k = os.environ.get("GEMINI_API_KEY")
    if not k:
        raise ApiError("GEMINI_API_KEY is not set (add it as a GitHub Actions secret).")
    return k


def _request(method, url, body=None, timeout=600, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"x-goog-api-key": _key(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        payload = r.read()
    return payload if raw else json.loads(payload)


def call(method, path_or_url, body=None, timeout=600, raw=False, tries=4):
    """HTTP call with retries on rate limits / server errors. Never prints the API key."""
    url = path_or_url if path_or_url.startswith("http") else f"{BASE}/{path_or_url}"
    for attempt in range(1, tries + 1):
        try:
            return _request(method, url, body, timeout, raw)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:800]
            if e.code in (429, 500, 502, 503, 504) and attempt < tries:
                wait = 20 * attempt
                print(f"  API {e.code}, retrying in {wait}s ({attempt}/{tries})", flush=True)
                time.sleep(wait); continue
            raise ApiError(f"HTTP {e.code} from {url.split('?')[0]}: {msg}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < tries:
                time.sleep(15 * attempt); continue
            raise ApiError(f"Network error calling {url.split('?')[0]}: {e}") from None


def _parts(resp):
    try:
        return resp["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        reason = json.dumps(resp.get("promptFeedback") or resp.get("candidates", [{}])[0].get("finishReason"))
        raise ApiError(f"No content returned (blocked or empty). Details: {reason}")


# ------------------------------------------------------------------ text (story writing)
def generate_json(prompt, temperature=1.0):
    if MOCK:
        from mock_data import MOCK_STORY
        return json.loads(json.dumps(MOCK_STORY))
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"}}
    models = [TEXT_MODEL] + [m for m in os.environ.get("TEXT_FALLBACKS", "gemini-flash-latest,gemini-flash-lite-latest").split(",") if m and m != TEXT_MODEL]
    resp, err = None, None
    for m in models:
        try:
            resp = call("POST", f"models/{m}:generateContent", body, timeout=180); break
        except ApiError as e:
            err = e; print(f"  {m} unavailable ({str(e)[:80]}...), trying the next model", flush=True)
    if resp is None: raise err
    text = "".join(p.get("text", "") for p in _parts(resp))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        s, e = text.find("{"), text.rfind("}")
        return json.loads(text[s:e + 1])


# ------------------------------------------------------------------ image (character reference sheet)
def generate_image(prompt, out_path, ref_images=()):
    if MOCK:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x88ccff:s=768x1344",
                        "-frames:v", "1", out_path], check=True)
        return out_path
    parts = [{"inlineData": {"mimeType": _mime(p), "data": _b64(p)}} for p in ref_images]
    parts.append({"text": prompt})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"aspectRatio": "9:16"}}}
    resp = call("POST", f"models/{IMAGE_MODEL}:generateContent", body, timeout=300)
    for p in _parts(resp):
        d = p.get("inlineData") or p.get("inline_data")
        if d and d.get("data"):
            open(out_path, "wb").write(base64.b64decode(d["data"]))
            return out_path
    raise ApiError("Image model returned no image.")


# ------------------------------------------------------------------ video (Gemini Omni Flash, Interactions API)
def _find_video(obj):
    """Walk the interaction JSON and return ('data', b64) or ('uri', url) for the first video output."""
    if isinstance(obj, dict):
        if obj.get("type") == "video" or str(obj.get("mime_type", obj.get("mimeType", ""))).startswith("video/"):
            if obj.get("data"): return "data", obj["data"]
            for k in ("uri", "file_uri", "fileUri", "url"):
                if obj.get(k): return "uri", obj[k]
        for v in obj.values():
            r = _find_video(v)
            if r: return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_video(v)
            if r: return r
    return None


def _download_uri(uri, out_path):
    # Files API resources need polling until ACTIVE; direct media links can be downloaded at once.
    if "/files/" in uri and ":download" not in uri and "alt=media" not in uri:
        name = uri.split("/v1beta/")[-1] if "/v1beta/" in uri else uri
        for _ in range(60):
            meta = call("GET", name, timeout=60)
            if meta.get("state") in ("ACTIVE", None):
                uri = meta.get("downloadUri") or meta.get("uri") or uri
                break
            time.sleep(5)
        if "alt=media" not in uri and ":download" not in uri:
            uri = uri + ("&" if "?" in uri else "?") + "alt=media"
    open(out_path, "wb").write(call("GET", uri, timeout=600, raw=True))


def generate_clip(prompt, ref_images, out_path, aspect="9:16", resolution="720p"):
    """One 3D story clip. ref_images keep Veer and Veera looking the same in every clip."""
    if MOCK:
        from mock_data import mock_clip
        return mock_clip(prompt, out_path)
    inp = [{"type": "image", "data": _b64(p), "mime_type": _mime(p)} for p in ref_images]
    inp.append({"type": "text", "text": prompt})
    body = {"model": VIDEO_MODEL, "input": inp,
            "response_format": {"type": "video", "aspect_ratio": aspect, "resolution": resolution},
            "background": False, "store": False, "stream": False}
    resp = call("POST", "interactions", body, timeout=900)
    # Long-running fallback: if the API answers with an id and a non-final status, poll it.
    for _ in range(90):
        if _find_video(resp) or resp.get("status") in ("completed", "failed", "cancelled", None):
            break
        time.sleep(10)
        resp = call("GET", f"interactions/{resp['id']}", timeout=120)
    if resp.get("status") == "failed":
        raise ApiError(f"Video generation failed: {json.dumps(resp.get('error', resp))[:600]}")
    found = _find_video(resp)
    if not found:
        raise ApiError(f"No video in response (possibly blocked by safety filters): {json.dumps(resp)[:600]}")
    kind, val = found
    if kind == "data":
        open(out_path, "wb").write(base64.b64decode(val))
    else:
        _download_uri(val, out_path)
    return out_path


# ------------------------------------------------------------------ voice (TTS)
def narrate(text, out_wav, style="Read this like a warm, gentle Indian storyteller telling a bedtime story to a 5-year-old, with a smile in your voice"):
    if MOCK:
        from mock_data import mock_voice
        return mock_voice(text, out_wav)
    if os.environ.get("VOICE_ENGINE") == "edge":
        return narrate_edge(text, out_wav)
    try:
        return _narrate_gemini(text, out_wav, style)
    except ApiError as e:
        print(f"  Gemini voice unavailable ({str(e)[:120]}...), using the free Edge voice instead", flush=True)
        return narrate_edge(text, out_wav)


def narrate_edge(text, out_wav):
    """Free backup narrator (Microsoft Edge online voices via the edge-tts package; no key needed)."""
    voice = os.environ.get("EDGE_VOICE", "en-IN-NeerjaNeural")
    mp3 = out_wav + ".mp3"
    text = text.replace("  ...  ", " ... ")
    r = subprocess.run([sys.executable, "-m", "edge_tts", "--voice", voice, "--rate=-8%", "--text", text,
                        "--write-media", mp3], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(mp3):
        raise ApiError("Edge voice failed: " + r.stderr[-400:])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", "24000", "-ac", "1", out_wav], check=True)
    os.remove(mp3)
    return out_wav


def _narrate_gemini(text, out_wav, style):
    body = {"contents": [{"parts": [{"text": f"{style}: {text}"}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}}}
    resp = call("POST", f"models/{TTS_MODEL}:generateContent", body, timeout=180, tries=2)
    for p in _parts(resp):
        d = p.get("inlineData") or p.get("inline_data")
        if d and d.get("data"):
            pcm = base64.b64decode(d["data"])
            rate = 24000
            mt = d.get("mimeType", "")
            if "rate=" in mt:
                rate = int(mt.split("rate=")[1].split(";")[0])
            _write_wav(out_wav, pcm, rate)
            return out_wav
    raise ApiError("TTS returned no audio.")


# ------------------------------------------------------------------ helpers
def _b64(path): return base64.b64encode(open(path, "rb").read()).decode()
def _mime(path): return "image/png" if path.lower().endswith(".png") else "image/jpeg"


def _write_wav(path, pcm, rate, ch=1, bits=16):
    hdr = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, ch, rate, rate * ch * bits // 8, ch * bits // 8, bits)
    open(path, "wb").write(hdr + b"data" + struct.pack("<I", len(pcm)) + pcm)
