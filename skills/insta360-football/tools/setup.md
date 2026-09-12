# Setup and command reference

Requirements: native Windows for the supplied MediaSDKTest wrapper; Python 3.11 or later; NumPy, SciPy and Pillow; FFmpeg and ffprobe on PATH. The renderer uses libx264, not GPU encoding. Local vision is optional and requires an already loaded image-capable OpenAI-compatible model. Query its `/v1/models` endpoint first. No script installs dependencies or loads models automatically.

Use an existing suitable environment or an isolated virtual environment:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install numpy scipy pillow
```

Use the selected interpreter consistently. Keep the SDK executable, DLLs and models together. Inspect `example/main.cc`, installed headers and executable help to verify the flags used by `sdk_export.py`. Resolve accessory enum values from that SDK; do not guess a lens-guard setting. No default accessory is supplied intentionally.

Examples below use placeholders that must be replaced with inspected local paths and settings. Run from the repository root.

```bash
python skills/insta360-football/scripts/sdk_export.py --source "D:/recordings/source.insv" --sdk-bin "C:/SDK/bin" --output "D:/work/samples" --start 180 --end 190 --sample 0.5 --accessory ACCESSORY_ID
```

The exporter is a dry-run until `--execute` is added. Omit `--sample` for consecutive master frames. It exports an extra ending frame for coverage; rendering truncates to the plan duration. `--resume` requires an identical manifest and validates existing images. Do not delete invalid cache files implicitly; review or choose a fresh output directory. SDK denoise can be selected with `--denoise`; ColorPlus stays disabled. No new SDK export is needed for interpolation-only changes.

```bash
python skills/insta360-football/scripts/reframe.py --plan "D:/work/approved-plan.json" --frames "D:/work/master" --source "D:/recordings/source.insv" --first-frame 5395 --input-fps 30000/1001 --output "D:/work/approved-linear.mp4"
```

The frame index is illustrative, not an exact 180-second claim. The renderer derives source audio start from `first-frame / input-fps`. Frame names must be source indices such as `5395.jpg`. Plan time starts at zero. Choose duration aligned to output frames and verify the actual source interval. Output filenames use ASCII letters, numbers, dash, underscore and dot. Existing outputs are refused.

```bash
python skills/insta360-football/scripts/vision_call.py --model LOADED_MODEL_ID --prompt "D:/work/frame-prompt.md" --image "D:/work/view.jpg" --output "D:/work/request-001.json"
```

Prepare the prompt from the asset with timestamp and view metadata. Each invocation makes one request. `--schema` optionally enforces a server-supported JSON contract, not semantic correctness. Remote endpoints require explicit user consent and `--allow-remote`; redirects are refused. Receipts retain responses, usage, model, elapsed time and failure status. Keep them private. Do not claim total usage when some requests lack counters.
