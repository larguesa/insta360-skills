"""Quadros da vista ampla (studio) direto do 8K, so nos instantes t0+0.25+i*0.5 (NVDEC + remap so 2 fps).
python extract_wide_frames.py --input ..\\eq8k_002.mp4 --start 120 --end 970.8 --outdir frames_1T"""
import argparse, os, subprocess, sys, time, cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio_view as sv
ap = argparse.ArgumentParser(); ap.add_argument("--input"); ap.add_argument("--start", type=float); ap.add_argument("--end", type=float); ap.add_argument("--outdir")
ap.add_argument("--hw", default="cuda"); a = ap.parse_args(); os.makedirs(a.outdir, exist_ok=True)
W, H, rate, fps = sv.probe(a.input)
mx, my = sv.maps(W, H, 0.30, 170, -44, 7, 0, 1920, 1080, (230, 880))
N = int((a.end - a.start) / 0.5); t0 = time.time()
hw = ["-hwaccel", a.hw] if a.hw else []
dec = subprocess.Popen(["ffmpeg", "-v", "error", *hw, "-ss", f"{a.start + 0.25:.3f}", "-t", f"{N * 0.5:.3f}", "-i", a.input, "-vf", "fps=2:start_time=0",
                        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
fs = W * H * 3; n = 0
while n < N:
    b = dec.stdout.read(fs)
    if len(b) < fs: break
    f = np.frombuffer(b, np.uint8).reshape(H, W, 3)
    img = cv2.resize(sv.remap(f, mx, my, W, 0), (1280, 433), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(a.outdir, f"f_{n:05d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 85]); n += 1
    if n % 100 == 0: print(n, round(time.time() - t0, 1), flush=True)
dec.kill(); print("done", n, "of", N, round(time.time() - t0, 1), flush=True)
