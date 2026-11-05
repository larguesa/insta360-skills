---
name: futsal-broadcast-draft
description: >-
  Turn a fixed Insta360 side-of-court futsal recording into a YouTube-ready
  broadcast cut: 3 locked zones, LLM zone labels (OpenRouter ZDR), lookahead
  reframe, scoreboard PNG overlay, and a publish pack. Use when the user asks
  to reframe/broadcast/edit a futsal Insta360 game, not for outdoor football
  and not for ball tracking.
---

# Futsal broadcast (draft → YouTube)

Generic skill (no venue presets). Intermediate files live under `work\`. Never delete originals (INSV/LRV). Never commit game `work\` or API keys. Log deviations and costs in `work\skill_review.md`.

**What worked (reference game):** MediaSDK 8K export → wide frames every 0.5 s → `openai/gpt-6.1-sol` frames mode (chunks of 16) → label correction without re-analysis → `render_zones.py` lookahead → PNG placar → YouTube pack. ~US$0.0038/s of game (~US$7/game). Model choice is judged by **watching rendered test videos**, not numeric zone scores.

## Scripts (keep)

| Script | Role |
|---|---|
| `stillness_check.py` | Step 2 — random-sample stillness on LRV |
| `studio_view.py` | Remap equirect → studio view (maps + probe) |
| `render_linear_zones.py` | Step 4 — still frames / short tests of locked zones |
| `extract_wide_frames.py` | Step 6 — NVDEC 8K → JPEG wide frames @ 2 fps |
| `label_zones.py` | Step 6 — OpenRouter zone labels (was `test_models.py`) |
| `patch_labels.py` | Correction pass — goals/dead-ball without re-analysis |
| `render_zones.py` | Step 7 — lookahead reframe (was `render_05.py`) |
| `concat_videos.py` | Concat halves |
| `placar_template_overlay.py` | Step 10 — PNG scoreboard, no clock |
| `youtube_thumb.py` | Step 11 — clean frame + user overlay PNG |

**Obsolete (do not use):** `make_blocks.py`, `analyze_blocks.py`, `scoreboard_overlay.py` (ASS+clock), 60 s video-block pipeline, any Luna/Gemini/qwen primary path. Dropped from this skill.

## Prerequisites

- Insta360 MediaSDK (8K equirect export with optical flow + direction lock).
- ffmpeg with NVENC/NVDEC, Python 3.11+, OpenCV, Pillow.
- OpenRouter API key in a **file** (e.g. `%USERPROFILE%\.openrouter_archivist_key`). Always pass `--key-file`. Validate with `GET /api/v1/key` before labelling (script does this). **Key-file beats env** — a stale `OPENROUTER_API_KEY` caused 401s.
- User PNG templates in the game root when available: scoreboard (`Modelo do placar.png`) and thumb overlay (`Frame para thumb.png`).

## Pipeline

### 1. Map files and start offsets

List INSV/LRV. Note which file is half 1 / half 2 and the usable start (skip warm-up). Example pattern: `_002` from ~02:00, `_003` full half. Record in `work\run_config.json`.

### 2. Stillness check (~10 random samples)

```bash
python scripts/stillness_check.py --lrv <file.lrv> --samples 10
```

Confirm the camera did not move. Fail → stop and tell the user.

### 3. Confirm full-court studio view

Export a short still or clip via MediaSDK / `studio_view.py`. Starting point that framed a full court from the side:

- yaw ≈ 7, pitch ≈ −44, fov 170, distortion 0.30
- crop height band ≈ `460:1760` (3840 path) or `230:880` (1920 path)

Show the user; iterate until both goals and the near sideline are in frame. **No venue preset** — re-find per gym.

### 4. Lock 3 zones (fov 100)

Privacy vs corners trade-off: laterals must cover corner kicks without showing faces in the near stands when possible. Iterate with `render_linear_zones.py --test` stills. A working lock (reference only — re-tune per gym):

| Zone | yaw | pitch | fov |
|---|---|---|---|
| 1 left | −34 | −23 | 100 |
| 2 centre | 7 | −36 | 100 |
| 3 right | 44 | −22 | 100 |

Save as `work\zones.json`. Get user OK before exporting the full game.

### 5. MediaSDK 8K export

Optical flow + direction lock → `work\eq8k_1T.mp4` / `eq8k_2T.mp4` (or `_002`/`_003`). Expect ~15–16 min wall per ~15 min half on a typical GPU workstation. Do **not** cut 60 s studio blocks for the LLM — that path is obsolete.

### 6. Wide frames + zone labels (Sol)

**6a. Extract frames** (GPU decode, every 0.5 s, same instants the labeler uses):

```bash
python scripts/extract_wide_frames.py \
  --input work/eq8k_1T.mp4 --start 120 --end 970.8 \
  --outdir work/frames_1T
```

Uses NVDEC (`--hw cuda`) + studio remap only on sampled frames (~100× faster than rendering a full wide video).

**6b. Label with Sol (frames mode):**

```bash
python scripts/label_zones.py \
  --model openai/gpt-6.1-sol --mode frames \
  --key-file %USERPROFILE%\.openrouter_archivist_key \
  --frames-dir work/frames_1T --t0 120 --dur 850.8 \
  --tag 1T --chunk-size 16 --resume
```

Rules baked into the prompt (do not reintroduce the old bug):

- At a **goal**, hold the **lateral** zone of that goal end ≥ **3 s** (shot through ~3 s after). Do **not** jump to centre at the goal instant.
- If the ball is **dead ≥ 5 s** (pre-game, timeout, post-game) → zone 2 (centre).
- ~~Removed~~: `After a goal / at kickoff use zone 2.`

Operational notes that matter:

- Chunks of **16 frames** (~8 s). Larger chunks (48) hit OpenRouter peak-load **502** (`provider_unavailable` / usage size).
- Always `--resume` + a small watcher that retries on 502 with backoff 30–120 s.
- Running context across chunks; for the 2nd half pass `--ctx-init-file` with the last 1T summary **plus** a note that teams switched ends.
- Run halves **sequentially** (not parallel) to ease peak limits.
- Cost reference: ~**US$0.0038/s** of game → ~**US$7/game**.

**Model selection:** decide by watching short rendered test videos with the user. Numeric zone-agreement scores misled (Luna looked best on a 5-region gt.csv but failed the full-game watch). Benchmark finding to record: Luna / Gemini-flash* / qwen failed the watch test; only Sol was acceptable.

### 7. Render with lookahead

```bash
python scripts/render_zones.py \
  --input work/eq8k_1T.mp4 --labels work/1T_labels.json \
  --output work/reenq_1T.mp4 \
  --yaws -34,7,44 --pitches -23,-36,-22 --fovs 100,100,100 \
  --hold 1.5 --lead 1.0 --ease 1.2
```
(Start/duration come from the labels file `t0` + `len(zones)*step`. Pass the locked yaw/pitch/fov from step 4.)

Defaults that worked: **hold ≥ 1.5 s**, movement starts **1.0 s early** (lookahead on future labels), ease **1.2 s**. Then concat:

```bash
python scripts/concat_videos.py --inputs work/reenq_1T.mp4 work/reenq_2T.mp4 --output work/jogo_reenq.mp4
```

### 8. Correction pass (no re-analysis)

User confirms goals and long stoppages while watching `jogo_reenq.mp4`. Build a patch JSON and apply:

```bash
python scripts/patch_labels.py \
  --labels work/1T_labels.json --patch work/1T_patch.json --out work/1T_labels_v2.json
# same for 2T, then re-render both halves + concat → jogo_reenq_v2.mp4
```

Patch schema: `{"goals":[{"t":316.0,"zone":1,"hold_before":3,"hold_after":3}], "centres":[[120.0,167.5]]}` (source-timeline seconds).

### 9. Milestones confirmation

Models invent goals. Mine candidates from label summaries if useful, but **always** confirm with the user:

- Final times in the concat video, scorer side, running score.
- Map jersey colours → home/away (example: white=home, blue=away) for the placar.
- Write `work/marcos.json` with `goals_confirmed[]` (`final_s`, `team` = `home`|`away`) and optional `overlay` boxes/delay.

### 10. Scoreboard overlay

Use the user's PNG template. **No clock.** Score updates **+1.5 s after each goal**.

```bash
python scripts/placar_template_overlay.py \
  --input work/jogo_reenq_v2.mp4 \
  --template "Modelo do placar.png" \
  --events work/marcos.json \
  --output work/jogo_final.mp4 \
  --still-dir work/placar_check
```

Show stills before/after a couple of goals; get user OK. Copy the final file to the game root when approved.

### 11. YouTube publish pack

Build thumb from a **clean** action frame + the user's `Frame para thumb.png` overlay (alpha):

```bash
python scripts/youtube_thumb.py \
  --video work/jogo_reenq_v2.mp4 --t <clean_s> \
  --overlay "Frame para thumb.png" --out youtube-thumb.jpg
```

Pack (do **not** upload until the user approves title/description/visibility):

- **Title:** `Futsal Sub14: A vs B (NxM)`
- **Description:** date, venue, final score, chapter timestamps (kickoff, goals, half).
- Thumb 1280×720, final mp4.

Publish only after explicit user approval (channel, public/unlisted, etc.).

## Costs / time reference (one ~30 min Sub14 game)

| Step | OpenRouter USD | Wall (approx.) |
|---|---|---|
| 1–4 map / stillness / view / zones | 0 | ~15–20 min (with iterations) |
| 5 MediaSDK 8K ×2 halves | 0 | ~15–16 min each |
| 6a extract_wide_frames ×2 | 0 | ~10 min each (NVDEC) |
| 6b Sol labels 1T+2T | **~7.0** | ~1.5–2.5 h (peak retries) |
| 7 render ×2 + concat | 0 | ~15 min/half + 1 min |
| 8 patch + re-render | 0 | ~30–40 min |
| 10 placar | 0 | ~10–15 min |
| 11 thumb + meta | 0 | ~5 min |
| **Total labels** | **~US$0.0038/s ≈ US$7/game** | |

## Agent checklist

- [ ] Key via `--key-file`, validated; never print the key; never commit it.
- [ ] Intermediates only under `work\`; originals untouched.
- [ ] No 60 s video blocks; frames path only for Sol.
- [ ] Chunk 16 + `--resume` + peak-load retry.
- [ ] Prompt: lateral hold on goals; centre on dead ≥5 s; no “centre after goal”.
- [ ] Model pick by watched test renders, not scores.
- [ ] Step 9 human goal confirmation before placar.
- [ ] Step 11 pack ready; upload only with approval.
- [ ] Deviations + costs appended to `work\skill_review.md`.
