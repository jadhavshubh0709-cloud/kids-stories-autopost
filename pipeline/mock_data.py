"""Offline stand-ins for the Gemini API (MOCK_GEMINI=1), used to test the pipeline without a key or network."""
import subprocess

MOCK_STORY = {
    "title": "The Last Laddoo",
    "moral": "sharing",
    "moral_line": "Sharing makes happiness bigger!",
    "question": "Who does your child share snacks with?",
    "music": "playful",
    "caption": "Only ONE laddoo... who gets it? 🍬\n\nWhat would your little one do? 👇\n\nA new story every day ✨ Follow @kahani.time.kids\n\n#kidsstories #moralstories #storytime #storiesforkids #bedtimestories #kidslearning #parentingindia #kahanitimekids",
    "scenes": [
        {"visual": "A cozy Indian living room in the evening. Veer and Veera run in and stop in surprise at a small table with one round orange laddoo on a steel plate. Slow push-in on their amazed faces.",
         "sound": "soft evening sounds", "narration": "One evening, Veer and Veera found just one laddoo on the table."},
        {"visual": "Veer and Veera both reach for the plate at the same time, frowning playfully and pulling it gently toward themselves. Medium shot, light comic tone.",
         "sound": "light playful sounds", "narration": "It's mine, said Veer. No, it's mine, said Veera."},
        {"visual": "A tiny brown sparrow lands on the window sill and chirps softly, looking at the laddoo with hungry eyes. The twins turn their heads toward the window.",
         "sound": "sparrow chirping", "narration": "Just then, a tiny sparrow came to the window. It looked very hungry."},
        {"visual": "Veera smiles with an idea, raises one finger, then carefully breaks the laddoo into three small pieces on the plate while Veer watches and smiles.",
         "sound": "gentle crumbling", "narration": "Veera had an idea. Let's make three pieces, one for each of us!"},
        {"visual": "The sparrow hops onto the table and pecks its piece while Veer and Veera eat theirs, then jump with joy, capes fluttering, warm golden light and sparkles.",
         "sound": "happy chirps", "narration": "The laddoo was small, but their smiles were very big!"},
    ],
}


STAGING = [
    {"bg": "village", "chars": [{"who": "meera", "place": "left", "action": "walk", "walk_to": "centre_left", "mood": "happy"},
                               {"who": "gappu", "place": "right", "action": "idle", "mood": "surprised"}],
     "props": [{"kind": "mango", "place": "ground_centre"}]},
    {"bg": "school", "chars": [{"who": "aarav", "place": "left", "action": "point", "mood": "cross"},
                              {"who": "anya", "place": "right", "action": "droop", "mood": "sad"}],
     "props": [{"kind": "plate", "state": "one", "place": "table"}], "say": [{"who": "aarav", "text": "It's mine!"}]},
    {"bg": "jungle", "chars": [{"who": "bandu", "place": "left", "action": "bounce", "mood": "happy"},
                              {"who": "chiku", "place": "centre", "action": "jump", "mood": "happy"},
                              {"who": "tara", "place": "right", "action": "wave", "mood": "smile"}],
     "props": [{"kind": "bird", "place": "sky", "motion": "bob"}], "say": [{"who": "prop", "text": "Chirp..."}]},
    {"bg": "home", "chars": [{"who": "veer", "place": "left", "action": "hero", "mood": "smile"},
                            {"who": "veera", "place": "right", "action": "wave", "mood": "happy"}],
     "props": [{"kind": "plate", "state": "three", "place": "table"}], "say": [{"who": "veera", "text": "Let's share!"}]},
    {"bg": "park", "chars": [{"who": "meera", "place": "left", "action": "jump", "mood": "happy"},
                            {"who": "gappu", "place": "right", "action": "jump", "mood": "happy"}],
     "props": [{"kind": "heart", "place": "sky", "motion": "float"}], "sparkle": True},
]
MOCK_STORY["cast"] = ["meera", "gappu"]
for _sc, _st in zip(MOCK_STORY["scenes"], STAGING): _sc.update(_st)


def mock_clip(prompt, out):
    n = abs(hash(prompt)) % 5
    colors = ["0xf4a261", "0x2a9d8f", "0xe76f51", "0x8ab17d", "0x6d597a"][n]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"color=c={colors}:s=720x1280:d=8,format=yuv420p",
                    "-f", "lavfi", "-i", "testsrc2=s=360x360:d=8",
                    "-f", "lavfi", "-i", "anoisesrc=d=8:c=pink:a=0.05",
                    "-filter_complex", "[0:v][1:v]overlay=180:300:shortest=1[v]",
                    "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-t", "8", out], check=True)
    return out


def mock_voice(text, out):
    """Tone per line, with 0.7 s of silence where the text has '...' (like a real narrator's pause)."""
    lines = [l for l in text.split("...") if l.strip()]
    filt, inputs = [], []
    for i, l in enumerate(lines):
        d = max(1.2, len(l.split()) / 2.6)
        inputs += ["-f", "lavfi", "-i", f"sine=f={300 + 40 * i}:d={d}", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=0.7"]
    n = len(inputs) // 4
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex",
                    "".join(f"[{k}:a]aresample=24000,aformat=channel_layouts=mono[a{k}];" for k in range(n)) +
                    "".join(f"[a{k}]" for k in range(n)) + f"concat=n={n}:v=0:a=1,volume=0.3", "-ar", "24000", "-ac", "1", out], check=True)
    return out
