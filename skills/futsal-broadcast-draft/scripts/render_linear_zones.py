"""Camera virtual linear (retilinea) que se move entre zonas fixas, com pan suavizado.
python render_linear_zones.py --input eq8k.mp4 --start 170 --end 360 --timeline tl.json --output out.mp4
  [--key zones] [--yaws -33,7,47] [--fovs 115,115,115] [--pitches=-20,-27,-20]  (valores negativos: use --pitches=...)
  [--ease 1.5] [--lead 0.5] [--hold 2] [--w 1920 --h 1080] [--encoder h264_nvenc] [--test frame.jpg --t 60]
timeline json: {"zones":[2,2,3,...]} um valor por segundo (1=esquerda,2=centro,3=direita; N zonas = len(yaws)),
segundo 0 = --start. Aceita tambem lista de objetos {"t":..,"zone":..}.
Yaw/pitch/fov de cada zona sao CALIBRADOS POR JOGO (SKILL.md, Passo 4); os defaults sao do jogo 2026-10-26."""
import argparse, json, math, subprocess, time, os, tempfile
ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True); ap.add_argument("--output")
ap.add_argument("--start", type=float, default=0); ap.add_argument("--end", type=float)
ap.add_argument("--timeline"); ap.add_argument("--key", default="zones")
ap.add_argument("--yaws", default="-33,7,47"); ap.add_argument("--fovs", default="115,115,115"); ap.add_argument("--pitches", default="-20,-27,-20")
ap.add_argument("--ease", type=float, default=1.5); ap.add_argument("--lead", type=float, default=0.5); ap.add_argument("--hold", type=int, default=2)
ap.add_argument("--w", type=int, default=1920); ap.add_argument("--h", type=int, default=1080); ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--encoder", default="h264_nvenc"); ap.add_argument("--cq", default="21")
ap.add_argument("--test", help="so um quadro: zona --zone no tempo --t (s, relativo ao arquivo)"); ap.add_argument("--zone", type=int, default=2); ap.add_argument("--t", type=float, default=0)
a = ap.parse_args()
Y = [float(v) for v in a.yaws.split(",")]; F = [float(v) for v in a.fovs.split(",")]; P = [float(v) for v in a.pitches.split(",")]
vf = lambda h: 2 * math.degrees(math.atan(math.tan(math.radians(h / 2)) * a.h / a.w))
def v360(y, p, h): return f"v360=input=e:output=flat:reset_rot=1:yaw={y:.3f}:pitch={p:.3f}:h_fov={h:.3f}:v_fov={vf(h):.3f}:w={a.w}:h={a.h}"
if a.test:
    z = a.zone - 1
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.t), "-i", a.input, "-frames:v", "1", "-vf", v360(Y[z], P[z], F[z]), a.test], check=True); raise SystemExit
tl = json.load(open(a.timeline, encoding="utf-8"))
z = tl[a.key] if isinstance(tl, dict) else [r["zone"] for r in sorted(tl, key=lambda r: r["t"])]
N = int(round((a.end - a.start))) if a.end else len(z)
z = (list(z) + [z[-1]] * N)[:N]
def hold(v, k):  # so muda se a nova zona se mantem por >= k segundos
    o, cur = [], v[0]
    for i, x in enumerate(v):
        if x != cur and all(v[j] == x for j in range(i, min(len(v), i + k))): cur = x
        o.append(cur)
    return o
z = hold(z, a.hold)
ch = [(i, z[i - 1] - 1, z[i] - 1) for i in range(1, N) if z[i] != z[i - 1]]
def cam(t):
    k = z[0] - 1; y, p, h = Y[k], P[k], F[k]
    for c, i, j in ch:
        s = (t - (c - a.lead)) / a.ease
        if s <= 0: break
        e = 0.5 - 0.5 * math.cos(math.pi * min(1, s))
        y, p, h = Y[i] + (Y[j] - Y[i]) * e, P[i] + (P[j] - P[i]) * e, F[i] + (F[j] - F[i]) * e
    return round(y, 3), round(p, 3), round(h, 3)
rows, prev = [], None
for f in range(N * a.fps):
    t = f / a.fps; c = cam(t)
    if c != prev:
        y, p, h = c; rows.append(f"{t:.4f} [enter] v360 yaw {y}, [enter] v360 pitch {p}, [enter] v360 h_fov {h}, [enter] v360 v_fov {vf(h):.3f};")
    prev = c
cmdf = os.path.splitext(a.output)[0] + "_cmd.txt"; open(cmdf, "w").write("\n".join(rows))
y0, p0, h0 = cam(0); t0 = time.time()
d, b = os.path.split(os.path.abspath(cmdf))
subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-v", "error", "-ss", str(a.start), "-t", str(N), "-i", a.input, "-map", "0:v:0", "-map", "0:a?",
                "-vf", f"sendcmd=f={b},{v360(y0, p0, h0)},setsar=1,fps={a.fps}", "-c:v", a.encoder, *(["-preset", "p5", "-cq", a.cq] if "nvenc" in a.encoder else ["-preset", "fast", "-crf", a.cq]),
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", os.path.abspath(a.output)], cwd=d, check=True)
print(json.dumps({"output": a.output, "seconds": N, "changes": len(ch), "render_min": round((time.time() - t0) / 60, 2)}), flush=True)
