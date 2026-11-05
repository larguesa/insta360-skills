"""Passo 2: a camera ficou parada? ~10 amostras ALEATORIAS do arquivo, alinhamento de bordas contra uma referencia.
python stillness_check.py --input VID_..._002.insv|eq.mp4|.lrv [--n 10] [--seed 0] [--max-shift 2.0] [--out res.json]
Funciona com qualquer formato que o ffmpeg decodifique (insv/lrv crus ou equirect exportado): compara o quadro inteiro.
Saida: deslocamento (px, na escala 960 de largura) e correlacao de bordas de cada amostra vs a 1a. Exit 2 = camera MOVEU (cancelar)."""
import argparse, json, random, subprocess, sys
import cv2, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--input", required=True); ap.add_argument("--n", type=int, default=10)
ap.add_argument("--seed", type=int); ap.add_argument("--max-shift", type=float, default=2.0); ap.add_argument("--min-corr", type=float, default=0.35); ap.add_argument("--out")
a = ap.parse_args()
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.input], capture_output=True, text=True).stdout)
rng = random.Random(a.seed); ts = sorted(rng.uniform(1, dur - 1) for _ in range(a.n))
def grab(t):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", a.input, "-frames:v", "1", "-vf", "scale=960:-2,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    h = len(p) // 960; return np.frombuffer(p[:960 * h], np.uint8).reshape(h, 960)
def edges(g): return cv2.GaussianBlur(cv2.Canny(cv2.GaussianBlur(g, (5, 5), 0), 50, 150).astype(np.float32), (7, 7), 0)
ref = edges(grab(ts[0])); win = cv2.createHanningWindow(ref.shape[::-1], cv2.CV_32F); res = []
for t in ts:
    e = edges(grab(t)); (dx, dy), _ = cv2.phaseCorrelate(ref * win, e * win)
    c = float(np.corrcoef(ref.ravel(), e.ravel())[0, 1]); sh = (dx * dx + dy * dy) ** 0.5
    res.append({"t": round(t, 2), "dx": round(dx, 2), "dy": round(dy, 2), "shift": round(sh, 2), "edge_corr": round(c, 3), "ok": sh <= a.max_shift and c >= a.min_corr})
moved = not all(r["ok"] for r in res)
out = {"input": a.input, "duration": round(dur, 1), "samples": res, "moved": moved, "max_shift": max(r["shift"] for r in res), "min_corr": min(r["edge_corr"] for r in res)}
print(json.dumps(out, indent=1))
if a.out: json.dump(out, open(a.out, "w"), indent=1)
sys.exit(2 if moved else 0)
