"""PNG scoreboard overlay (no clock). Score updates --delay seconds after each goal.

python placar_template_overlay.py --input jogo_reenq.mp4 --template placar.png --events marcos.json --output jogo_final.mp4
"""
import argparse, json, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True); ap.add_argument("--template", required=True)
ap.add_argument("--events", required=True); ap.add_argument("--output", required=True)
ap.add_argument("--delay", type=float, default=1.5); ap.add_argument("--encoder", default="h264_nvenc")
ap.add_argument("--still-dir", help="escreve frames de checagem (antes/depois de um gol)")
a = ap.parse_args()
E = json.load(open(a.events, encoding="utf-8-sig"))
tpl = Image.open(a.template).convert("RGBA")
hb = tuple(E.get("overlay", {}).get("home_box", [778, 28, 906, 116]))
ab = tuple(E.get("overlay", {}).get("away_box", [1013, 28, 1141, 116]))
delay = E.get("overlay", {}).get("score_delay_s", a.delay)

def font_for(box):
    h = box[3] - box[1]
    size = max(28, int(h * 0.72))
    for name in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf", "Arial"):
        try: return ImageFont.truetype(name, size)
        except Exception: pass
    return ImageFont.load_default()

def make(h, w):
    im = tpl.copy(); dr = ImageDraw.Draw(im)
    for box, val in ((hb, str(h)), (ab, str(w))):
        f = font_for(box)
        # clear box interior lightly transparent white already; draw digit centered
        bb = dr.textbbox((0, 0), val, font=f); tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x = box[0] + (box[2] - box[0] - tw) / 2 - bb[0]
        y = box[1] + (box[3] - box[1] - th) / 2 - bb[1]
        dr.text((x, y), val, font=f, fill=(20, 30, 60, 255))
    return im

goals = sorted(E["goals_confirmed"], key=lambda g: g["final_s"])
# segments: (t0,t1,home,away)
segs = []; hs = aws = 0; t0 = 0.0
for g in goals:
    t_upd = g["final_s"] + delay
    segs.append((t0, t_upd, hs, aws))
    if g["team"] == "home": hs += 1
    else: aws += 1
    t0 = t_upd
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.input], capture_output=True, text=True).stdout)
segs.append((t0, dur + 1, hs, aws))
print("segments", [(round(s,1), round(e,1), h, w) for s, e, h, w in segs], flush=True)

td = tempfile.mkdtemp(prefix="placar_")
pngs = []
for i, (s, e, h, w) in enumerate(segs):
    p = os.path.join(td, f"p_{i}_{h}_{w}.png"); make(h, w).save(p); pngs.append(p)

# still checks around first and a mid goal
if a.still_dir:
    os.makedirs(a.still_dir, exist_ok=True)
    g0, g1 = goals[0], goals[2]
    for name, t in (("before_g1", g0["final_s"] - 1), ("after_g1", g0["final_s"] + delay + 0.5),
                    ("before_g3", g1["final_s"] - 1), ("after_g3", g1["final_s"] + delay + 0.5)):
        # composite one frame
        raw = os.path.join(a.still_dir, name + "_raw.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(max(0, t)), "-i", a.input, "-frames:v", "1", raw], check=True)
        base = Image.open(raw).convert("RGBA")
        # find which score at t
        hh = sum(1 for g in goals if g["final_s"] + delay <= t and g["team"] == "home")
        ww = sum(1 for g in goals if g["final_s"] + delay <= t and g["team"] == "away")
        out = Image.alpha_composite(base, make(hh, ww))
        out.convert("RGB").save(os.path.join(a.still_dir, name + ".jpg"), quality=90)

# ffmpeg filter: chain overlays with enable
# [0:v][1:v]overlay=enable='between(t,s,e)'[v1]; ...
inp = ["-i", os.path.abspath(a.input)]
for p in pngs: inp += ["-i", p]
fc = []; last = "[0:v]"
for i, (s, e, h, w) in enumerate(segs):
    out = f"[v{i}]" if i < len(segs) - 1 else "[vout]"
    # last segment open-ended
    en = f"between(t\\,{s:.3f}\\,{e:.3f})" if i < len(segs) - 1 else f"gte(t\\,{s:.3f})"
    fc.append(f"{last}[{i+1}:v]overlay=0:0:format=auto:enable='{en}'{out}")
    last = out
filt = ";".join(fc)
cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-v", "error", *inp, "-filter_complex", filt, "-map", "[vout]", "-map", "0:a?",
       "-c:v", a.encoder, "-preset", "p5", "-cq", "21", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
       os.path.abspath(a.output)]
print("ffmpeg...", flush=True)
subprocess.run(cmd, check=True)
print("ok", a.output, flush=True)
