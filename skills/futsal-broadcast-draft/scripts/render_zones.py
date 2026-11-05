"""Render 3 zonas com rotulos a cada 0,5 s e lookahead. python render_zones.py --labels labels_x.json --input eq8k.mp4 --output out.mp4
Lookahead: a mudanca so vale se a nova zona se mantem >= --hold s; o movimento comeca --lead s ANTES do instante rotulado e dura --ease s."""
import argparse, json, math, subprocess, os, time
ap = argparse.ArgumentParser(); ap.add_argument("--labels"); ap.add_argument("--input"); ap.add_argument("--output")
ap.add_argument("--yaws", default="-34,7,44"); ap.add_argument("--pitches", default="-23,-36,-22"); ap.add_argument("--fovs", default="100,100,100")
ap.add_argument("--hold", type=float, default=1.5); ap.add_argument("--lead", type=float, default=1.0); ap.add_argument("--ease", type=float, default=1.2)
ap.add_argument("--w", type=int, default=1920); ap.add_argument("--h", type=int, default=1080); ap.add_argument("--fps", type=int, default=30)
a = ap.parse_args(); L = json.load(open(a.labels)); st = L["step"]; z = L["zones"]; N = len(z); dur = N * st
Y = [float(v) for v in a.yaws.split(",")]; P = [float(v) for v in a.pitches.split(",")]; F = [float(v) for v in a.fovs.split(",")]
vf = lambda h: 2 * math.degrees(math.atan(math.tan(math.radians(h / 2)) * a.h / a.w))
k = max(1, int(round(a.hold / st))); o, cur = [], z[0]
for i, x in enumerate(z):
    if x != cur and all(z[j] == x for j in range(i, min(N, i + k))): cur = x
    o.append(cur)
ch = [(i * st, o[i - 1] - 1, o[i] - 1) for i in range(1, N) if o[i] != o[i - 1]]
def cam(t):
    q = o[0] - 1; y, p, h = Y[q], P[q], F[q]
    for c, i, j in ch:
        s = (t - (c - a.lead)) / a.ease
        if s <= 0: break
        e = 0.5 - 0.5 * math.cos(math.pi * min(1, s)); y, p, h = Y[i] + (Y[j] - Y[i]) * e, P[i] + (P[j] - P[i]) * e, F[i] + (F[j] - F[i]) * e
    return round(y, 3), round(p, 3), round(h, 3)
rows, prev = [], None
for f in range(int(dur * a.fps)):
    t = f / a.fps; c = cam(t)
    if c != prev: y, p, h = c; rows.append(f"{t:.4f} [enter] v360 yaw {y}, [enter] v360 pitch {p}, [enter] v360 h_fov {h}, [enter] v360 v_fov {vf(h):.3f};")
    prev = c
cmdf = os.path.splitext(a.output)[0] + "_cmd.txt"; open(cmdf, "w").write("\n".join(rows))
y0, p0, h0 = cam(0); t0 = time.time(); d, b = os.path.split(os.path.abspath(cmdf))
v = f"v360=input=e:output=flat:reset_rot=1:yaw={y0}:pitch={p0}:h_fov={h0}:v_fov={vf(h0):.3f}:w={a.w}:h={a.h}"
subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-v", "error", "-ss", str(L["t0"]), "-t", str(dur), "-i", os.path.abspath(a.input), "-map", "0:v:0", "-map", "0:a?",
                "-vf", f"sendcmd=f={b},{v},setsar=1,fps={a.fps}", "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", os.path.abspath(a.output)], cwd=d, check=True)
print(json.dumps({"output": a.output, "changes": len(ch), "render_s": round(time.time() - t0, 1)}))
