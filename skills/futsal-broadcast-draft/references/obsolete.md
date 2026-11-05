# Obsolete paths (do not revive)

- 60 s studio video blocks (`make_blocks.py`) and `analyze_blocks.py` LLM-on-clip pipeline.
- API proxies (`blocos_ref_api`) — unnecessary once labelling from local frames.
- Primary use of `google/gemini-*-flash*`, `qwen/qwen3.5-*`, `openai/gpt-6-luna` for full-game labels (failed user watch tests).
- `scoreboard_overlay.py` ASS + burnt-in clock (replaced by `placar_template_overlay.py`).
- Prompt line `After a goal / at kickoff use zone 2.` (forced centre-on-goal).
- Judging models by numeric zone-agreement with a small gt.csv (misses lag and uncovered plays).
