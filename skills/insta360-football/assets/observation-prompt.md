# Football observation

Source timestamp: FILL_IN_SECONDS
View pose: FILL_IN_YAW_PITCH_FOV
Coordinate convention: normalized image coordinates, x rightward and y downward, both 0..1.

First compare adjacent timestamps for a confirmed stoppage: most on-court athletes stationary and no active play. During a timeout or wait for kickoff/restart, recommend a smooth return to the calibrated geometric court/field center and a stationary hold. Do not search for the ball or follow isolated walking/referee movement. Keep this fixed center rather than recomputing a player centroid. Resume when actual play starts, even if only a few players move. A missing ball or a single still image is not evidence of inactivity. Report the inactivity evidence in the observation; a script needs an explicitly validated state contract and planner override to execute this policy.

During active play, primary question: WHERE IS THE PLAY concentrated, and where is the active players' collective attention directed? Do not start and stop with asking where the ball is.
Combine active-player positions with apparent gaze/head direction, rotational orientation of torso and hips, posture, running direction, opponent interaction and passing/receiving space. Use gaze only when resolvable; do not invent eye direction from tiny faces.
Follow where several engaged players turn and converge, not merely the densest group or the largest pixel motion. Exclude referees, spectators and substitutes.
Use supplied adjacent timestamps to disambiguate movement, changes of possession and preparation for a pass. A visible ball is supporting evidence; an invisible ball does not prevent a defensible play-region inference.
Report one target: visible_ball, play_region, or unknown.
For a visible ball, give its image coordinates and concise visual evidence, but retain the surrounding play and receiving space as the editorial context.
For a play region, describe its center, the engaged players and the observed attention/body-direction cues supporting it. Explicitly mark inference; never call this a verified ball coordinate. If cues disagree, lower confidence and recommend a wider defensible composition.
For unknown, explain the missing visual evidence and recommend a defensible hold or wider view.
Keep observations separate from camera commands. Return a short factual observation.
