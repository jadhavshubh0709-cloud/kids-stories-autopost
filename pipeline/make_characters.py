"""One-time: creates the Veer & Veera reference images that every video clip copies, so the twins look the same daily.

Usage: python3 pipeline/make_characters.py   -> assets/characters/twins.png, veer.png, veera.png
Look at them on GitHub. If you don't like them, delete the files and run again (each run gives new designs).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gemini_api, story_writer

OUT = os.path.join(HERE, "..", "assets", "characters")
BASE = ("3D animated cartoon character design in a cute, high-quality family-movie style, soft studio lighting, "
        "plain light background, full body, front view, no text. ")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    twins = os.path.join(OUT, "twins.png")
    if not os.path.exists(twins):
        gemini_api.generate_image(BASE + "Two characters standing side by side, smiling and waving: " + story_writer.CHARACTERS, twins)
        print("wrote", twins)
    for name in ("veer", "veera"):
        p = os.path.join(OUT, f"{name}.png")
        if not os.path.exists(p):
            gemini_api.generate_image(BASE + f"Only {name.capitalize()} from the reference image, alone, same exact design, "
                                      "turnaround: front view and side view.", p, ref_images=[twins])
            print("wrote", p)
