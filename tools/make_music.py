"""Original, copyright-free background music for @twin.heros story reels.
Synthesized from scratch with numpy (no samples), so there are no licensing issues.

Usage: python3 tools/make_music.py   -> music/<mood>.m4a (about 60 s each)
Moods: playful (fun stories), gentle (bedtime / emotional), adventure (brave / exciting stories)
"""
import os, subprocess
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "music")
rng = np.random.default_rng(3)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def lp(x, c): b, a = butter(2, c / (SR / 2), "low"); return lfilter(b, a, x)
def hp(x, c): b, a = butter(2, c / (SR / 2), "high"); return lfilter(b, a, x)
def tt(n): return np.arange(n) / SR

def glock(m, dur):          # bright bell / xylophone
    n = int(dur * SR); t = tt(n); f = midi(m)
    x = np.sin(2*np.pi*f*t) + 0.35*np.sin(2*np.pi*f*2.76*t)*np.exp(-t*9) + 0.15*np.sin(2*np.pi*f*5.4*t)*np.exp(-t*16)
    return x * np.exp(-t * 4.5) * np.minimum(1, t / 0.002)

def musicbox(m, dur):
    n = int(dur * SR); t = tt(n); f = midi(m)
    x = np.sin(2*np.pi*f*t) + 0.25*np.sin(2*np.pi*f*3*t)*np.exp(-t*6)
    return x * np.exp(-t * 2.2) * np.minimum(1, t / 0.003)

def uke(m, dur):             # plucked string (Karplus-Strong)
    n = int(dur * SR); p = int(SR / midi(m))
    buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return lp(out, 3500)

def pad(notes, dur, cut=900):
    n = int(dur * SR); t = tt(n); x = np.zeros(n)
    for m in notes:
        for d in (-0.06, 0.06): x += np.sin(2*np.pi*midi(m+d)*t) + 0.2*np.sin(2*np.pi*midi(m+d)*2*t)
    e = np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.4)
    return lp(x, cut) * e / (2 * len(notes))

def bass(m, dur):
    n = int(dur * SR); t = tt(n); f = midi(m)
    return (np.sin(2*np.pi*f*t) + 0.3*np.sin(4*np.pi*f*t)) * np.exp(-t * 3) * np.minimum(1, t / 0.01)

def shaker(dur=0.08):
    n = int(dur * SR); return hp(rng.standard_normal(n), 6000) * np.exp(-tt(n) * 60) * 0.3

def softkick():
    n = int(0.25 * SR); t = tt(n); f = 45 + 60*np.exp(-t*35)
    return np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-t*12)

def put(buf, s, pos, g=1.0):
    pos = int(pos)
    if pos >= len(buf): return
    e = min(len(buf), pos + len(s)); buf[pos:e] += s[:e-pos] * g

def master(x, name):
    x = x - x.mean(); x = np.tanh(x / (np.abs(x).max() + 1e-9) * 1.3)
    f = int(2 * SR); x[-f:] *= np.linspace(1, 0, f); x[:2000] *= np.linspace(0, 1, 2000)
    x = x / np.abs(x).max() * 0.85
    st = np.stack([x, np.roll(x, int(0.01 * SR)) * 0.96], 1)
    os.makedirs(OUT, exist_ok=True); wav = os.path.join(OUT, name + ".wav")
    wavfile.write(wav, SR, (st * 32767).astype(np.int16))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "aac", "-b:a", "160k", wav[:-4] + ".m4a"], check=True)
    os.remove(wav); print("wrote", name)

def arrange(bpm, prog, melody, bars, lead, rhythm, beat_drums=True, lead_gain=0.5):
    b = 60 / bpm * SR; n = int(b * 4 * bars) + SR
    L, U, P, B, D = (np.zeros(n) for _ in range(5))
    for bar in range(bars):
        root, ch = prog[bar % len(prog)]; s = bar * 4 * b
        put(P, pad(ch, 4 * b / SR), s)
        put(B, bass(root, 1.8), s); put(B, bass(root + 7, 1.0), s + 2 * b)
        for pos, idx in rhythm: put(U, uke(ch[idx % len(ch)] - 12, 0.6), s + pos * b, 0.8)
        for pos, m, d in melody[bar % len(melody)]:
            if bar >= 2: put(L, lead(m, d * 60 / bpm + 0.6), s + pos * b)
        if beat_drums and bar >= 1:
            for q in range(8): put(D, shaker(), s + q * b / 2, 1.0 if q % 2 else 0.6)
            put(D, softkick(), s); put(D, softkick(), s + 2 * b, 0.8)
    return 0.30 * P + 0.45 * B + 0.40 * U + lead_gain * L + 0.5 * D

def playful():   # bouncy, happy, 112 bpm, C major
    prog = [(36, [60, 64, 67]), (41, [60, 65, 69]), (43, [59, 62, 67]), (36, [60, 64, 67]),
            (33, [57, 60, 64]), (41, [60, 65, 69]), (43, [59, 62, 67]), (43, [62, 65, 67])]
    mel = [[(0, 72, .5), (.5, 76, .5), (1, 79, 1), (2.5, 76, .5), (3, 72, 1)],
           [(0, 77, .5), (.5, 76, .5), (1, 74, .5), (1.5, 72, .5), (2, 69, 1.5)],
           [(0, 71, .5), (.5, 74, .5), (1, 79, 1), (2, 77, .5), (2.5, 76, .5), (3, 74, 1)],
           [(0, 72, 1.5), (2, 79, .5), (2.5, 81, .5), (3, 79, 1)],
           [(0, 76, .5), (.5, 72, .5), (1, 69, 1), (2.5, 72, .5), (3, 76, 1)],
           [(0, 77, .5), (.5, 81, .5), (1, 84, 1), (2, 81, .5), (3, 77, 1)],
           [(0, 79, .5), (.5, 77, .5), (1, 76, .5), (1.5, 74, .5), (2, 71, 1)],
           [(0, 74, .5), (.5, 77, .5), (1, 79, 1), (2, 84, 2)]]
    rhy = [(0, 0), (.5, 1), (1, 2), (1.5, 1), (2, 0), (2.5, 1), (3, 2), (3.5, 1)]
    return arrange(112, prog, mel, 28, glock, rhy)

def gentle():    # soft music box, 76 bpm, F major
    prog = [(41, [65, 69, 72]), (38, [62, 65, 69]), (46, [62, 65, 70]), (36, [64, 67, 70])]
    mel = [[(0, 77, 1), (1, 81, 1), (2, 84, 2)], [(0, 82, 1), (1, 81, 1), (2, 77, 2)],
           [(0, 79, 1), (1, 77, 1), (2, 74, 2)], [(0, 76, 1), (1, 79, 1), (2, 77, 2)]]
    rhy = [(0, 0), (1, 1), (2, 2), (3, 1)]
    return arrange(76, prog, mel, 20, musicbox, rhy, beat_drums=False, lead_gain=0.6)

def adventure(): # brave, marching, 120 bpm, D major-ish
    prog = [(38, [62, 66, 69]), (43, [62, 67, 71]), (45, [64, 69, 73]), (38, [62, 66, 69])]
    mel = [[(0, 74, .5), (.5, 74, .5), (1, 78, .5), (1.5, 81, 1.5), (3, 78, 1)],
           [(0, 79, .5), (.5, 81, .5), (1, 83, 1), (2, 81, .5), (2.5, 79, .5), (3, 78, 1)],
           [(0, 76, .5), (.5, 78, .5), (1, 81, 1), (2, 85, 1), (3, 81, 1)],
           [(0, 86, 1.5), (1.5, 81, .5), (2, 78, 1), (3, 74, 1)]]
    rhy = [(0, 0), (.5, 0), (1, 1), (1.5, 2), (2, 0), (2.5, 0), (3, 1), (3.5, 2)]
    return arrange(120, prog, mel, 30, glock, rhy)

if __name__ == "__main__":
    for name, fn in [("playful", playful), ("gentle", gentle), ("adventure", adventure)]:
        master(fn(), name)
