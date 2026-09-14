---
name: insta360-football
description: Use when editing Insta360 football match footage. Produce supervised, smooth rectilinear play-region videos for futsal, small-sided and full-size pitches.
version: 1.1.0
author: Sofia Vicarius
metadata:
  hermes:
    editorial_name: Insta360 Football Editor
    editorial_description: Local, evidence-led football reframing with calibrated geometry and smooth camera motion.
    requires_tools: [terminal, read_file, write_file]
    requires_toolsets: [terminal, file]
---

# Insta360 Football Editor

## Scope

Convert fixed-camera Insta360 recordings into conventional 16:9 match video with original audio. Use the Media SDK for stitching and stabilization, an explicitly authorized local or remote vision model, or a human editor, for observations, and deterministic FFmpeg rendering for the virtual camera. This skill covers futsal, society and outdoor football with the same editorial priorities, not identical camera settings.

Do not treat a model response as verified ball tracking. The proven result is approximate play-region framing with user-approved smooth motion. Do not automatically substitute Deep Track: it repeatedly failed on the small, fast ball in the reference footage.

## Whole-match baseline and method boundary

Read [Whole-match semantic reframing](references/whole-match.md) before scaling. Preserve execution method, editorial target and actual model/route independently. Do not substitute SDK rendering for requested Studio GUI editing. Use semantic play-region observations, not the experimental `motion_plan.py` pixel centroid. Approval of a manual sample does not qualify a different automated planner.

## Workflow and approval gates

1. **Discover read-only.** Inventory the authorized recording folder, identify recording groups and inspect streams with ffprobe. An X5 INSV may contain both lens video tracks in one file. Verify rather than require an older-camera file pair. Keep proprietary trailers intact: do not trim/remux INSV before SDK processing. LRV is a proxy, not the final detail source.
2. **Agree on scope.** Confirm source interval, output destination, aspect ratio, original audio, compute budget and camera position. Start with a short representative sample including movement in both directions. Ask only for information not available from files.
3. **Calibrate before inference.** Export a full-resolution panorama frame. Compare rectilinear views at several yaw angles and FOVs. Set both FOVs and square pixels. A 90-degree horizontal FOV is a starting candidate, not a universal setting. Confirm horizon, pitch, seams, goals, near and far touchlines, and body proportions. Studio angles may use a different origin/sign.
4. **Analyze offline every 0.5 seconds initially.** Export selected full-resolution frames, then generate overlapping perspective views. Use neighboring timestamps and explicit view pose. Preserve observations and receipts. Distinguish visible ball, inferred play region and unknown. Enlarge claimed ball locations before accepting them. Same-model crop verification is an additional check, not independent ground truth.
5. **Approve a camera plan.** Translate only validated evidence into relative clip-time yaw keyframes. Keep pitch/FOV fixed in the initial renderer. During uncertainty, hold a defensible composition or manually choose a wider calibrated FOV; do not manufacture ball coordinates. Reconcile observations across overlapping chunks before rendering. Preserve the approved plan separately from raw model output.
6. **Export the master.** For long clips, prefer continuous SDK panorama-video export over dense 8K JPEG sequences; selected frames remain appropriate for analysis and short tests. Use the original INSV and the correct lens accessory. Keep SDK settings, frame indices, source FPS and export provenance. Run one GPU workload at a time. Start with the dry-run exporter and its bounded frame count; explicitly authorize expensive jobs.
7. **Render continuous motion.** Use shared PCHIP-derived tangents with cubic Hermite interpolation, zero endpoint tangents and absolute v360 rotations (`reset_rot=1`). Do not independently ease every half-second interval to zero speed. Retain held final poses. Reject excessive speed rather than silently altering approved keyframes.
8. **Verify and deliver.** Validate dimensions, square pixels, frame count, duration, full decoding, original source preservation and audio synchronization. Watch fast transitions, reversals, occlusions, seams and both ends of the pitch. Automated checks are necessary, not a replacement for visual approval. Deliver a separately named variant, measured timing and explicit limitations.

## Generalize by calibration, not by copying angles

For futsal, inspect wall rebounds, spectators close to the touchline and rapid changes of possession. For society, inspect larger lateral coverage, fencing and far-side ball visibility. For full-size pitches, inspect long passes, aerial balls, distant players and whether the source actually resolves the ball. All formats prioritize the active play region and receiving space rather than chasing every player. Camera height, placement and orientation determine the angular limits. Recalibrate when any of them changes, including a moved tripod or a new recording orientation.

The example plan is synthetic and only demonstrates the contract. Its yaw bounds and pitch are not presets for every ground. The renderer currently supports constant pitch/FOV, a bounded yaw range without wraparound, and one clip. A 360-degree seam crossing requires an unwrapped-angle planner before this renderer can safely support it.

## Quality and reuse

Reuse stitched frames and observations when changing only camera interpolation. Changing SDK denoise requires a new SDK export with otherwise identical settings. Test one image-quality feature at a time on about ten seconds with the approved camera plan. The reference SDK denoise A/B produced little perceptible benefit. ColorPlus improved colors in the user's Studio test, not missing detail; manual 4K export did not solve the noise. Capture settings and poor illumination were suspected, not independently established as the cause.

Do not claim AI super-resolution: none was found in the inspected desktop SDK. More output pixels do not restore detail missing from a narrow sphere crop. Evaluate small-ball preservation, trails and waxy textures before enabling denoise broadly. Central dead zones, hysteresis, dynamic zoom and jerk-limited planning are future experiments, not features of the approved baseline.

## Tools and supporting material

- [Setup and commands](tools/setup.md)
- [Geometry and observations](references/editorial.md)
- [Evidence and limitations](references/validation.md)
- [Whole-match semantic workflow and recovery](references/whole-match.md)
- [Example plan](assets/example-plan.json)
- [Observation prompt](assets/observation-prompt.md)
- `scripts/sdk_export.py`: bounded export and provenance-checked resume.
- `scripts/vision_call.py`: one explicit request with raw response, usage and failure receipt.
- `scripts/reframe.py`: plan checks and verified local render.

## Safety and acceptance checklist

- [ ] Originals and proprietary metadata preserved; separate output paths.
- [ ] Accessory and SDK version confirmed against installed package.
- [ ] Geometry and short composition sample approved.
- [ ] Uncertainty and approximate framing labeled honestly.
- [ ] No model-generated shell commands executed.
- [ ] No private frames or recordings sent remotely without consent.
- [ ] Motion, duration, image geometry, audio and full decoding checked.
- [ ] Every request, retry and verification included in usage accounting where counters exist.
- [ ] Local inference distinguished from orchestration tokens and subscription billing.
- [ ] Same prompt/model/planner as the approved baseline; any replacement revalidated.
- [ ] First live play, both goal areas, reversal, uncertainty and joins checked in continuous clips for every period.
- [ ] Resume tested; optional native-project generation cannot block MP4 recovery.
- [ ] No full-match expansion before representative visual acceptance (internal review when unattended work is authorized).
