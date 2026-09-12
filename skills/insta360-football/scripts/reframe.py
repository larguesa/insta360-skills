"""Render an approved, local 360 camera plan. No SDK or model calls."""
import argparse
import json
import math
from fractions import Fraction
from pathlib import Path
import subprocess
import time


def vfov(hfov, width, height):
    if not (0 < hfov < 180 and width > 0 and height > 0):
        raise ValueError('Invalid rectilinear geometry')
    return math.degrees(2 * math.atan(math.tan(math.radians(hfov / 2)) * height / width))


def camera(plan):
    import numpy as np
    from scipy.interpolate import PchipInterpolator, CubicHermiteSpline
    duration = float(plan['duration'])
    fps = float(Fraction(str(plan['output_fps'])))
    width, height = plan['output_size']
    low, high = plan['yaw_limits']
    pitch = float(plan['pitch'])
    if not (math.isfinite(duration) and 0 < duration <= 3600 and 1 <= fps <= 120):
        raise ValueError('Invalid duration or output FPS')
    if not (isinstance(width, int) and isinstance(height, int) and width % 2 == height % 2 == 0):
        raise ValueError('Output dimensions must be positive even integers')
    vertical = vfov(float(plan['hfov']), width, height)
    if not (-180 <= low < high <= 180 and -90 < pitch < 90):
        raise ValueError('Invalid angles')
    keys = plan['keyframes']
    times = np.array([k['t'] for k in keys], dtype=float)
    angles = np.array([k['yaw'] for k in keys], dtype=float)
    if len(keys) < 2 or not np.all(np.isfinite(times)) or not np.all(np.isfinite(angles)):
        raise ValueError('At least two finite keyframes required')
    if times[0] != 0 or np.any(np.diff(times) <= 0) or times[-1] > duration:
        raise ValueError('Keyframes must start at zero, increase, and stay within duration')
    if np.any(angles < low) or np.any(angles > high):
        raise ValueError('Keyframe outside calibrated angular bounds')
    slopes = PchipInterpolator(times, angles).derivative()(times)
    slopes[0] = slopes[-1] = 0
    # ponytail: approved C1 monotone path; C2/jerk-limited planning is a separate upgrade.
    curve = CubicHermiteSpline(times, angles, slopes)
    count = round(duration * fps)
    if count < 1 or abs(count / fps - duration) > 1e-7:
        raise ValueError('Duration must be an integer number of output frames')
    grid = np.arange(count) / fps
    yaw = curve(np.minimum(grid, times[-1]))
    speed = np.diff(yaw) * fps
    if np.min(yaw) < low - 1e-7 or np.max(yaw) > high + 1e-7:
        raise ValueError('Interpolated trajectory exceeds bounds')
    if len(speed) and np.max(np.abs(speed)) > float(plan['max_speed']) + 1e-6:
        raise ValueError('Camera exceeds speed limit: revise approved keyframes, do not clamp silently')
    return grid, yaw, vertical


def write_commands(path, grid, yaw):
    rows = []
    previous = None
    for t, angle in zip(grid, yaw):
        angle = round(float(angle), 6)
        if angle != previous:
            rows.append(f'{t:.9f} [enter] v360 yaw {angle:.6f};')
        previous = angle
    with path.open('x', encoding='utf-8') as f:
        f.write('\n'.join(rows))


def probe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
                       capture_output=True, check=True, timeout=45)
    return json.loads(p.stdout)


def render(plan, source, frames, first, output, input_fps, timeout=1200):
    grid, yaw, vertical = camera(plan)
    source, frames, output = source.resolve(), frames.resolve(), output.resolve()
    if not source.is_file() or not frames.is_dir() or first < 0:
        raise ValueError('Source, frame directory and first frame must be valid')
    rate = float(Fraction(input_fps))
    if not 1 <= rate <= 240:
        raise ValueError('Invalid source FPS')
    info = probe(source)
    streams = [s for s in info['streams'] if s['codec_type'] == 'video']
    if not streams or abs(float(Fraction(streams[0]['r_frame_rate'])) - rate) > .001:
        raise ValueError('Input FPS differs from source; probe the original')
    if not any(s['codec_type'] == 'audio' for s in info['streams']):
        raise ValueError('Source has no audio; this renderer requires the agreed original audio')
    source_start = first / rate
    if source_start + plan['duration'] > float(info['format']['duration']) + 1 / rate:
        raise ValueError('Requested interval exceeds source duration')
    for n in range(first, first + math.ceil(plan['duration'] * rate)):
        if not (frames / f'{n}.jpg').is_file():
            raise ValueError(f'Missing source frame {n}')
    output.parent.mkdir(parents=True, exist_ok=True)
    commands = output.with_suffix('.commands.txt')
    partial = output.with_name(output.stem + '.partial.mp4')
    report_path = output.with_suffix('.report.json')
    for p in (output, partial, commands, report_path, output.with_suffix('.log')):
        if p.exists():
            raise FileExistsError(f'Refusing to overwrite {p}')
    # A generated local basename avoids filtergraph path/escaping injection.
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.' for c in commands.name):
        raise ValueError('Use an ASCII output filename with letters, digits, dash or underscore')
    write_commands(commands, grid, yaw)
    width, height = plan['output_size']
    filt = (f'sendcmd=f={commands.name},v360=input=e:output=flat:reset_rot=1:'
            f'yaw={yaw[0]}:pitch={plan["pitch"]}:h_fov={plan["hfov"]}:v_fov={vertical}:'
            f'w={width}:h={height},setsar=1,fps={plan["output_fps"]}')
    cmd = ['ffmpeg', '-hide_banner', '-nostdin', '-n', '-threads', '4',
           '-framerate', input_fps, '-start_number', str(first), '-i', str(frames / '%d.jpg'),
           '-ss', str(source_start), '-i', str(source), '-map', '0:v:0', '-map', '1:a:0',
           '-t', str(plan['duration']), '-vf', filt, '-filter_threads', '4',
           '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '192k', '-map_metadata', '-1',
           '-metadata', 'title=Approximate play-region framing', '-movflags', '+faststart', str(partial)]
    before = source.stat()
    start = time.monotonic()
    with output.with_suffix('.log').open('x', encoding='utf-8') as log:
        subprocess.run(cmd, cwd=output.parent, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout)
    result = probe(partial)
    video = next(s for s in result['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in result['streams'] if s['codec_type'] == 'audio')
    if ((video['width'], video['height']) != (width, height) or video['sample_aspect_ratio'] != '1:1'
            or int(video['nb_frames']) != len(grid)
            or abs(float(result['format']['duration']) - plan['duration']) > .1):
        raise RuntimeError('Output failed geometry, frame count or duration verification')
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(partial), '-f', 'null', '-'],
                   capture_output=True, check=True, timeout=timeout)
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError('Source changed during processing')
    partial.rename(output)
    report = {'output': str(output), 'source_start_seconds': source_start,
              'duration': result['format']['duration'], 'frames': len(grid),
              'seconds': time.monotonic() - start, 'output_bytes': output.stat().st_size,
              'audio_channels': audio['channels'], 'decode_verified': True,
              'source_size_mtime_preserved': True, 'ball_tracking_verified': False,
              'new_model_calls': 0, 'plan': plan}
    with report_path.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--source', type=Path)
    p.add_argument('--frames', type=Path)
    p.add_argument('--first-frame', type=int, default=0)
    p.add_argument('--input-fps', default='30000/1001')
    p.add_argument('--output', type=Path)
    p.add_argument('--check', action='store_true', help='Validate motion only, without rendering')
    a = p.parse_args()
    plan = json.loads(a.plan.read_text(encoding='utf-8'))
    if a.check:
        grid, yaw, vertical = camera(plan)
        print(json.dumps({'frames': len(grid), 'yaw_min': float(min(yaw)),
                          'yaw_max': float(max(yaw)), 'vfov': vertical}))
    else:
        if not all((a.source, a.frames, a.output)):
            p.error('--source, --frames and --output are required without --check')
        print(json.dumps(render(plan, a.source, a.frames, a.first_frame, a.output, a.input_fps)))


if __name__ == '__main__':
    main()
