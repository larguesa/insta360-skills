"""Vista "Studio" (perspectiva generalizada, como o Insta360 Studio) + recorte da quadra.

frame:  python studio_view.py frame --input eq.mp4 --t 282 --output f.jpg [view] [--drift d.json]
video:  python studio_view.py video --input eq.mp4 --start 170 --end 360 --output out.mp4 [view] [--drift d.json]

view: --distortion 0.30 --fov 170 --pitch -32 --yaw 7 --roll 0 --w 3840 --h 2160 --crop 640:1880
Modelo de projecao: r = (d+1)*sin(theta)/(d+cos(theta)), d = distortion (0 = retilinea,
1 = estereografica); fov = horizontal. O frame e renderizado em w x h e recortado nas linhas
crop (y0:y1). Drift: yaw(t) = yaw - dx_deg(t), igual ao model_view.py (interpolacao linear).
"""
import argparse, json, subprocess, sys
import cv2, numpy as np

def drift_fn(path):
    if not path: return lambda t: 0.0
    pts = sorted((float(k), v["dx_deg"]) for k, v in json.load(open(path)).items())
    def f(t):
        if t <= pts[0][0]: return pts[0][1]
        for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
            if t <= t1: return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
        return pts[-1][1]
    return f

def src_rot(y, p, r):
    y, p, r = np.radians([y, p, r])
    Ry = np.array([[np.cos(y), 0, np.sin(y)], [0, 1, 0], [-np.sin(y), 0, np.cos(y)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    Rz = np.array([[np.cos(r), -np.sin(r), 0], [np.sin(r), np.cos(r), 0], [0, 0, 1]])
    return Ry @ Rx @ Rz

def maps(eqw, eqh, distortion=0.30, fov=170, pitch=-32, yaw=7, roll=0, w=3840, h=2160, crop=None, srot=None):
    """Retorna (mx, my) float32 para cv2.remap. mx sem modulo (aplicar deslocamento de drift e depois % eqw)."""
    d = distortion
    th = np.linspace(0, np.radians(179), 20000); rr = (d + 1) * np.sin(th) / (d + np.cos(th))
    ok = np.cumprod(np.concatenate([[True], np.diff(rr) > 0])).astype(bool); th, rr = th[ok], rr[ok]
    rmax = (d + 1) * np.sin(np.radians(fov / 2)) / (d + np.cos(np.radians(fov / 2)))
    y0, y1 = crop if crop else (0, h)
    u, v = np.meshgrid((np.arange(w) + .5 - w / 2) / (w / 2) * rmax,
                       (np.arange(y0, y1) + .5 - h / 2) / (w / 2) * rmax)
    t = np.interp(np.hypot(u, v), rr, th, right=np.nan); phi = np.arctan2(v, u)
    x = np.sin(t) * np.cos(phi); y = -np.sin(t) * np.sin(phi); z = np.cos(t)
    R, P = np.radians(roll), np.radians(pitch)
    x, y = x * np.cos(R) - y * np.sin(R), x * np.sin(R) + y * np.cos(R)
    y, z = y * np.cos(P) + z * np.sin(P), -y * np.sin(P) + z * np.cos(P)
    if srot is not None:  # source (e.g. LRV) orientation differs from the SDK export: rotate after yaw
        Y = np.radians(yaw); x, z = x * np.cos(Y) + z * np.sin(Y), -x * np.sin(Y) + z * np.cos(Y); yaw = 0
        v = np.stack([x, y, z], -1) @ src_rot(*srot).T; x, y, z = v[..., 0], v[..., 1], v[..., 2]
    lon = np.degrees(np.arctan2(x, z)) + yaw; lat = np.degrees(np.arcsin(np.clip(y, -1, 1)))
    return ((lon / 360 + .5) * eqw).astype(np.float32), ((.5 - lat / 180) * eqh).astype(np.float32)

def probe(path):
    o = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                 "stream=width,height,r_frame_rate", "-of", "csv=p=0", path], text=True).strip().split(",")
    n, dd = o[2].split("/"); return int(o[0]), int(o[1]), o[2], float(n) / float(dd)

def remap(f, mx, my, eqw, dx):
    sx = np.mod(mx - dx / 360.0 * eqw, eqw).astype(np.float32)   # yaw - dx
    return cv2.remap(f, sx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["frame", "video"])
    ap.add_argument("--input", required=True); ap.add_argument("--output", required=True)
    ap.add_argument("--t", type=float, default=0); ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--end", type=float); ap.add_argument("--drift")
    for k, dv in [("distortion", .30), ("fov", 170.), ("pitch", -32.), ("yaw", 7.), ("roll", 0.)]:
        ap.add_argument("--" + k, type=float, default=dv)
    ap.add_argument("--w", type=int, default=3840); ap.add_argument("--h", type=int, default=2160)
    ap.add_argument("--crop", default="640:1880")
    ap.add_argument("--lrv", action="store_true", help="input is dual-fisheye LRV/insv-preview: ffmpeg dfisheye->e first")
    ap.add_argument("--lrv_fov", type=float, default=200); ap.add_argument("--lrv_eqw", type=int, default=3328)
    ap.add_argument("--src_rot", default=None, help="yaw,pitch,roll of the source vs SDK export, e.g. -1,-7,-1.5"); ap.add_argument("--cq", default="21")
    a = ap.parse_args()
    crop = tuple(map(int, a.crop.split(":"))) if a.crop else None
    W, H, rate, fps = probe(a.input); dr = drift_fn(a.drift)
    vf = []
    if a.lrv:
        W, H = a.lrv_eqw, a.lrv_eqw // 2
        vf = ["-vf", f"v360=dfisheye:e:ih_fov={a.lrv_fov}:iv_fov={a.lrv_fov}:w={W}:h={H}"]
    srot = tuple(map(float, a.src_rot.split(","))) if a.src_rot else None
    mx, my = maps(W, H, a.distortion, a.fov, a.pitch, a.yaw, a.roll, a.w, a.h, crop, srot)
    oh, ow = mx.shape
    if a.mode == "frame":
        b = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", str(a.t), "-i", a.input, *vf, "-frames:v", "1",
                                     "-f", "rawvideo", "-pix_fmt", "bgr24", "-"])
        f = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        cv2.imwrite(a.output, remap(f, mx, my, W, dr(a.t)), [cv2.IMWRITE_JPEG_QUALITY, 90]); return
    dur = (a.end - a.start) if a.end else None
    tt = ["-t", str(dur)] if dur else []
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(a.start), *tt, "-i", a.input, *vf,
                            "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{ow}x{oh}",
                            "-r", rate, "-i", "-", "-ss", str(a.start), *tt, "-i", a.input, "-map", "0:v", "-map", "1:a?",
                            "-c:v", "h264_nvenc", "-preset", "p5", "-cq", a.cq, "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", a.output], stdin=subprocess.PIPE)
    n, fs = 0, W * H * 3
    while True:
        b = dec.stdout.read(fs)
        if len(b) < fs: break
        f = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        enc.stdin.write(remap(f, mx, my, W, dr(a.start + n / fps)).tobytes()); n += 1
        if n % 600 == 0: print(n, flush=True)
    enc.stdin.close(); enc.wait(); print("done", n, flush=True)

if __name__ == "__main__":
    main()