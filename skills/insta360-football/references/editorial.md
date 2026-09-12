# Geometry and observations

For rectilinear output with square pixels:

`vfov = degrees(2 * atan(tan(radians(hfov / 2)) * height / width))`

Set `v360=input=e:output=flat:reset_rot=1`, both FOVs, and `setsar=1`. Specifying only horizontal FOV leaves an independent vertical default and can distort player proportions. Wide-angle edge stretching is a separate issue.

Use overlapping perspective views rather than raw dual fisheye images. Record view yaw, pitch, both FOVs, dimensions and source timestamp beside each image. A pixel in a perspective crop is not a panorama coordinate. Either calibrate its ray transformation and test signs against static poses, or choose a manually verified view-center anchor; do not apply equirectangular coordinate formulas to perspective pixels.

Sample every 0.5 seconds with adjacent-frame context. Declare one coordinate convention, such as normalized 0..1, and reject out-of-range values instead of guessing another scale. Retain unknown observations. Reject suspiciously fixed coordinates across changing images, contradictory visibility claims and spectator/player confusion. The ball must be inside the proposed marked region, not merely somewhere in an enlarged crop.

Use a wider approved composition or a defensible hold during occlusion. Long uncertainty requires human review. Preserve receiving space during passes without inventing a predicted ball position. Avoid a forced stop at every observation: shared tangents give continuous velocity. This baseline is C1, not guaranteed continuous acceleration or bounded jerk.

For multiple render chunks, plan the complete trajectory first or explicitly carry boundary position and velocity. Independently zeroing each chunk's endpoints would reintroduce visible stops. The bundled renderer is deliberately a single-clip tool.
