"""Offline stand-ins for the Gemini API (MOCK_GEMINI=1), used to test the pipeline without a key or network."""
import subprocess

MOCK_STORY = {
    "title": "The Last Laddoo",
    "moral": "sharing",
    "moral_line": "Sharing makes happiness bigger!",
    "question": "Who does your child share snacks with?",
    "music": "playful",
    "caption": "Only ONE laddoo... who gets it? 🍬\n\nWhat would your little one do? 👇\n\nA new Twin Heroes story every day ✨ Follow @twin.heros\n\n#kidsstories #moralstories #storytime #storiesforkids #bedtimestories #kidslearning #parentingindia #twinheros",
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
    d = max(1.5, len(text.split()) / 2.6)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=f=330:d={d}",
                    "-af", "volume=0.3", "-ar", "24000", "-ac", "1", out], check=True)
    return out
