# Insta360 Skills

Agent-assisted editing of Insta360 futsal footage into a YouTube-ready broadcast cut.

## Skill

- **[futsal-broadcast-draft](skills/futsal-broadcast-draft/SKILL.md)** — fixed side-of-court Insta360 futsal → 3-zone broadcast cut, OpenRouter (ZDR) zone labels, PNG scoreboard, YouTube pack. This is the path that produced a full approved Sub14 game (~US labels/game).

## Install with your AI agent

Copy and send this instruction to your agent:

`	ext
Install the futsal-broadcast-draft skill from https://github.com/larguesa/insta360-skills. Read its SKILL.md, use the skill installation mechanism supported by your environment, and tell me which prerequisites or permissions are still needed before processing any footage.
`

You can give this instruction to agents such as **Hermes**, **OpenClaw**, **ChatGPT Desktop**, **Claude Code / Cowork**, or other assistants with access to files and tools. Installation and execution depend on the capabilities and permissions available in your agent; not every app or mode supports installing skills or running local tools.

## The story behind this skill

Read Ricardo Pupo Larguesa's article [Testando os limites da visão artificial](https://aintuicao.scale.press/post/2026/09/27/testando-os-limites-da-visao-artificial) (in Portuguese) for the experiments, limitations and supervised workflow that led to this work.

## License

This repository is licensed under the [MIT License](LICENSE). Third-party SDKs, models and tools remain subject to their own licenses and terms.

## SDK downloads and documentation

Download SDK packages through the official developer resources and follow their current access and licensing requirements. No proprietary SDK binaries or models are bundled here.

- [Official developer documentation and SDK access](https://github.com/Insta360Develop/Insta360-Developer_Docs)
- [Desktop Media SDK repository and download instructions](https://github.com/Insta360Develop/Desktop-MediaSDK-Cpp)
- [Desktop Camera SDK repository and download instructions](https://github.com/Insta360Develop/Desktop-CameraSDK-Cpp)
- [Desktop Media SDK guide](https://insta360develop.github.io/Insta360-Developer_Docs/en/x/desktop/media/)
- [Canonical Media SDK documentation source](https://github.com/Insta360Develop/Insta360-Developer_Docs/blob/main/docs/en/sdk/x-ace-go/desktop/media.md)
- [OSC camera-control API](https://github.com/Insta360Develop/Insta360_OSC)
- [FFmpeg download](https://ffmpeg.org/download.html) and [v360 documentation](https://ffmpeg.org/ffmpeg-filters.html#v360)

The Windows reference used Media SDK 3.1.5. Inspect the installed headers, example/main.cc and executable help before using a different version. Camera control and OSC are not required for editing existing recordings.

## Layout

- skills/futsal-broadcast-draft/: futsal broadcast pipeline (SKILL.md + scripts + references).

Keep originals, generated frames, faces, model responses, credentials and proprietary SDK files outside this repository.

## Getting started

Use an existing Python environment with NumPy, OpenCV and Pillow, or create a separate virtual environment. Keep FFmpeg and ffprobe on PATH (NVENC/NVDEC recommended).

Read [skills/futsal-broadcast-draft/SKILL.md](skills/futsal-broadcast-draft/SKILL.md). OpenRouter key via --key-file only; never commit keys or game work\ folders.

All repository documentation, prompts, comments and user-facing script output are in English. Nothing uploads recordings automatically. Review each short sample before authorizing longer processing.
