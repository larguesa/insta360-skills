# Football observation

Source timestamp: FILL_IN_SECONDS
View pose: FILL_IN_YAW_PITCH_FOV
Coordinate convention: normalized image coordinates, x rightward and y downward, both 0..1.

Inspect the active play region using the supplied adjacent timestamps.
Report one target: visible_ball, play_region, or unknown.
For a visible ball, give its image coordinates and concise visual evidence.
For a play region, describe the active players and direction of play, explicitly marking inference.
For unknown, explain the missing visual evidence and recommend a defensible hold or wider view.
Keep observations separate from camera commands. Return a short factual observation.
