"""Label broadcast zones every 0.5 s from wide frames (or video). Running context across chunks.

Default path that worked: openai/gpt-6.1-sol --mode frames --chunk-size 16 --resume
with --frames-dir from extract_wide_frames.py. Key via --key-file only (validated first).

python label_zones.py --model openai/gpt-6.1-sol --mode frames --key-file KEY \
  --frames-dir frames_1T --t0 120 --dur 850.8 --tag 1T --chunk-size 16 --resume
"""
import argparse, base64, json, os, re, subprocess, sys, time, urllib.error, urllib.request
ap = argparse.ArgumentParser(); ap.add_argument("--model"); ap.add_argument("--mode"); ap.add_argument("--key-file"); ap.add_argument("--tag")
ap.add_argument("--src", default="wide_170_360.mp4"); ap.add_argument("--t0", type=float, default=170); ap.add_argument("--dur", type=float, default=190); ap.add_argument("--frames-dir"); ap.add_argument("--ctx-init-file"); ap.add_argument("--out-prefix", default="")
ap.add_argument("--resume", action="store_true", help="retoma de partial/jsonl se existir")
ap.add_argument("--chunk-size", type=int, default=0, help="override chunk size (frames or labels)")
a = ap.parse_args()
if not a.key_file:
    raise SystemExit("--key-file is required (do not use env OPENROUTER_API_KEY; it may be stale)")
KEY = open(a.key_file, encoding="utf-8").read().strip()
# validate key before spending (GET /api/v1/key); key-file always wins over env
try:
    kr = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(kr, timeout=30) as resp:
        kd = json.loads(resp.read().decode())
    data = kd.get("data", kd) if isinstance(kd, dict) else {}
    print("key ok", {k: data.get(k) for k in ("label", "is_free_tier", "limit_remaining") if isinstance(data, dict)}, flush=True)
except Exception as e:
    raise SystemExit(f"key validation failed: {e}")
STEP = 0.5
PROMPT = """Indoor futsal filmed by a FIXED camera at the side of the court. The images/video show the WHOLE court: left goal at the left, right goal at the right.
A virtual broadcast camera must follow the play. For EACH half-second instant listed, decide where it should point: zone 1 = left third (left goal end), 2 = centre, 3 = right third (right goal end).
Follow where the PLAY is concentrated (engaged players, ball carrier and those converging, attack direction). Ignore referees, idle goalkeepers, bench, spectators.
When play stops for a short moment keep the zone where it stopped until play resumes. At a GOAL hold the lateral zone of that goal end for at least 3 seconds (cover the shot through ~3 s after); do NOT jump to centre at the goal instant. After the hold, kickoff/restart may use zone 2. If the ball is dead for >=5 seconds (pre-game, timeout, post-game, long stoppage) use zone 2 (centre). Be responsive: switch as soon as an attack enters a third.
Context so far (running summary): {ctx}
{what}
Return ONLY JSON: {{"labels":[{{"t":<seconds from clip start, multiple of 0.5>,"zone":1-3}}...],"summary":"<=60 words running summary: who attacks which side, where play is at the end"}}
You MUST return exactly {n} labels, t = 0, 0.5, 1.0 ... {last}."""
def post(msg):
    body = {"model": a.model, "provider": {"zdr": True}, "usage": {"include": True}, "messages": [{"role": "user", "content": msg}]}
    err = None
    for k in range(12):
        try:
            t0 = time.time(); r = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", json.dumps(body).encode(), {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            raw = urllib.request.urlopen(r, timeout=900).read()
            j = json.loads(raw)
            if "choices" not in j or not j["choices"]:
                err = "no_choices " + re.sub(r"Bearer \S+", "Bearer ***", raw.decode("utf-8", "replace")[:500])
                peak = "high demand" in err.lower() or "provider_unavailable" in err.lower() or """maximum usage size""" in err.lower()
                wait = (min(120, 30 * (k + 1)) if peak else min(60, 5 * (k + 1)))
                print(f"post no_choices retry {k+1}/12 wait={wait}s peak={peak}", flush=True)
                time.sleep(wait); continue
            txt = j["choices"][0]["message"]["content"]
            if not txt or not isinstance(txt, str):
                err = "empty_content " + json.dumps({k2: j.get(k2) for k2 in ("error", "id", "model")})[:400]
                time.sleep(min(60, 5 * (k + 1))); continue
            m = re.search(r"\{.*\}", txt, re.S)
            if not m:
                err = "no_json " + txt[:300].replace("\n", " ")
                time.sleep(min(60, 5 * (k + 1))); continue
            o = json.loads(m.group()); u = j.get("usage", {})
            return o, u.get("cost", 0) or 0, u.get("total_tokens", 0), time.time() - t0
        except Exception as e:
            err = str(e)
            if isinstance(e, urllib.error.HTTPError):
                try: err += " " + e.read().decode("utf-8", "replace")[:400]
                except Exception: pass
            elif hasattr(e, "read"):
                try: err += " " + e.read().decode("utf-8", "replace")[:300]
                except Exception: pass
            err = re.sub(r"Bearer \S+", "Bearer ***", err)[:500]
            print(f"post retry {k+1}/12: {err[:200]}", flush=True)
            time.sleep(min(60, 5 * (k + 1)))
    raise RuntimeError(err)
def frame(t):
    if a.frames_dir: return open(os.path.join(a.frames_dir, "f_%05d.jpg" % int(round((t - 0.25) / STEP))), "rb").read()
    return subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", a.src, "-frames:v", "1", "-vf", "scale=1280:-2", "-q:v", "5", "-f", "mjpeg", "-"], capture_output=True).stdout
def clip(s, d):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(s), "-t", str(d), "-i", a.src, "-vf", "scale=1280:-2,fps=10", "-c:v", "libx264", "-crf", "28", "-preset", "fast", "-an", "-movflags", "+faststart", "-f", "mp4", "pipe_tmp_%s.mp4" % a.tag, "-y"], check=True)
    b = open("pipe_tmp_%s.mp4" % a.tag, "rb").read(); os.remove("pipe_tmp_%s.mp4" % a.tag); return b
N = int(a.dur / STEP); chunk = a.chunk_size or (16 if a.mode == "frames" else 120)  # 16 frames (~8 s) avoids peak-load 502; video 60 s
zones = [None] * N; ctx = (open(a.ctx_init_file, encoding="utf-8").read().strip() if a.ctx_init_file else ""); cost = tok = 0; T0 = time.time()
log_path = f"{a.out_prefix}log_{a.tag}.jsonl"
partial_path = f"{a.out_prefix}partial_{a.tag}.json"
labels_path = f"{a.out_prefix}labels_{a.tag}.json"
done_upto = 0
if a.resume and os.path.exists(partial_path):
    try:
        P = json.load(open(partial_path, encoding="utf-8"))
        if P.get("model") == a.model and P.get("t0") == a.t0 and P.get("step") == STEP and len(P.get("zones", [])) == N:
            zones = P["zones"]; cost = P.get("cost", 0) or 0; tok = P.get("tokens", 0) or 0; ctx = P.get("ctx", "") or ""
            done_upto = next((i for i, z in enumerate(zones) if z is None), N)
            print(f"resume partial: done_upto={done_upto}/{N} cost={cost:.4f} ctx_len={len(ctx)}", flush=True)
        else:
            print("partial mismatch; starting fresh", flush=True)
    except Exception as e:
        print(f"partial load fail: {e}; starting fresh", flush=True)
log_mode = "a" if (a.resume and done_upto > 0 and os.path.exists(log_path)) else "w"
if log_mode == "w" and done_upto == 0 and os.path.exists(log_path) and not a.resume:
    pass  # overwrite intentionally
log = open(log_path, log_mode, encoding="utf-8")
for c0 in range(0, N, chunk):
    if c0 < done_upto:
        continue
    n = min(chunk, N - c0); s = c0 * STEP
    if a.mode == "frames":
        what = f"These {n} frames are taken every 0.5 s; each is preceded by its time label (seconds from clip start)."
        msg = [{"type": "text", "text": PROMPT.format(ctx=ctx or "(start)", what=what, n=n, last=(n - 1) * STEP)}]
        for i in range(n):
            msg += [{"type": "text", "text": f"t={i * STEP:.1f}"}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(frame(s + i * STEP + 0.25)).decode()}}]
    else:
        what = f"The video clip lasts {n * STEP:.1f} s. Label every 0.5 s."
        msg = [{"type": "text", "text": PROMPT.format(ctx=ctx or "(start)", what=what, n=n, last=(n - 1) * STEP)},
               {"type": "video_url", "video_url": {"url": "data:video/mp4;base64," + base64.b64encode(clip(s, n * STEP)).decode()}}]
    o, c, tk, dt = post(msg); cost += c; tok += tk; ctx = o.get("summary", "")
    got = 0
    for x in o.get("labels", []):
        try:
            i = int(round(float(x["t"]) / STEP))
            if 0 <= i < n: zones[c0 + i] = int(x["zone"]); got += 1
        except Exception: pass
    log.write(json.dumps({"chunk_start_s": a.t0 + s, "n": n, "got": got, "cost": c, "tokens": tk, "secs": round(dt, 1), "summary": ctx}, ensure_ascii=False) + "\n"); log.flush()
    json.dump({"step": STEP, "t0": a.t0, "zones": zones, "model": a.model, "cost": cost, "tokens": tok, "wall_s": round(time.time() - T0, 1), "ctx": ctx, "filled_so_far": sum(1 for z in zones if z is not None)}, open(partial_path, "w", encoding="utf-8"))
    print(f"{a.tag} chunk {s:.0f}s got {got}/{n} US$ {c:.4f} {dt:.0f}s total=${cost:.4f}", flush=True)
# preencher lacunas com o ultimo valor
last = next((z for z in zones if z), 2); miss = 0
for i in range(N):
    if zones[i] is None: zones[i] = last; miss += 1
    last = zones[i]
json.dump({"step": STEP, "t0": a.t0, "zones": zones, "model": a.model, "cost": cost, "tokens": tok, "wall_s": round(time.time() - T0, 1), "filled": miss}, open(labels_path, "w", encoding="utf-8"))
log.close()
print(json.dumps({"tag": a.tag, "cost": round(cost, 4), "tokens": tok, "wall_s": round(time.time() - T0, 1), "filled": miss, "labels": labels_path}))
