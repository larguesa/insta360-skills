# Evidence and limits

## Reference results

A one-minute X5 futsal excerpt was approved in rectilinear 90-degree horizontal FOV, 1080p 16:9, with original audio content and a smooth camera path. Analysis used 120 half-second observations from a local Qwen3.5 9B model. Earlier Gemma E4B ball coordinates were rejected; a Gemma 12B image-processing attempt failed. Model names are historical evidence, not required dependencies or performance guarantees.

The first linear run took about 44 minutes including development and debugging. Reusing frames for the smooth-motion correction took about 4 minutes 46 seconds for rendering and validation. These are historical measurements, not throughput promises.

The user found little difference in a ten-second SDK denoise comparison. Studio ColorPlus improved colors, while a manual 4K export still looked similar in detail. Do not call this a proven restoration workflow.

## Regression requirements

Test proportional FOV, strict increasing timestamps, angular bounds, finite numbers, speed limits, held endpoints and nonzero velocity through a sustained pan. Test sendcmd as zero-order hold between commands. Repeated identical absolute rotations should produce identical frames, and a commanded final pose should match a static render.

Before delivery, probe streams and fully decode. Check audible synchronization near the start and end. The renderer transcodes source audio to AAC, preserving content rather than claiming byte identity. Its source size/mtime check is not a cryptographic integrity proof. Keep independent source hashes when stronger verification is required.

## Explicit limits

This repository provides a supervised workflow and reusable building blocks. It does not implement automatic perspective-view generation, trustworthy ball detection, automatic observation-to-angle conversion, full-match orchestration, dynamic FOV or camera seam unwrapping. Model request success and valid JSON do not prove perception accuracy. SDK success exit codes do not prove frame export success. Automated tests do not establish visual quality on untested pitch types.
