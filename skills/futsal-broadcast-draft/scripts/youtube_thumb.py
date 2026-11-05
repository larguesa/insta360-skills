"""Build a YouTube thumbnail: clean frame from video + user PNG overlay (alpha).

python youtube_thumb.py --video jogo_reenq.mp4 --t 196.5 --overlay "Frame para thumb.png" --out youtube-thumb.jpg
"""
import argparse, subprocess
from pathlib import Path
from PIL import Image

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--t", type=float, required=True, help="timestamp seconds (clean action frame)")
    ap.add_argument("--overlay", required=True, help="user PNG with alpha (e.g. Frame para thumb.png)")
    ap.add_argument("--out", default="youtube-thumb.jpg")
    ap.add_argument("--size", default="1280x720")
    a = ap.parse_args()
    w, h = map(int, a.size.split("x"))
    tmp = Path(a.out).with_suffix(".frame.png")
    subprocess.check_call([
        "ffmpeg", "-y", "-v", "error", "-ss", f"{a.t:.3f}", "-i", a.video,
        "-frames:v", "1", "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
        str(tmp),
    ])
    base = Image.open(tmp).convert("RGBA")
    over = Image.open(a.overlay).convert("RGBA").resize((w, h), Image.LANCZOS)
    out = Image.alpha_composite(base, over).convert("RGB")
    out.save(a.out, quality=92)
    tmp.unlink(missing_ok=True)
    print("wrote", a.out, out.size)

if __name__ == "__main__":
    main()
