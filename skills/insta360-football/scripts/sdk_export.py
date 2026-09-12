"""Bounded Windows Media SDK frame export. Dry-run unless --execute is supplied."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from reframe import probe


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--sdk-bin', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--start', required=True, type=float)
    p.add_argument('--end', required=True, type=float)
    p.add_argument('--size', default='7680x3840')
    p.add_argument('--accessory', required=True, type=int)
    p.add_argument('--sample', type=float, help='Seconds between analysis frames; omit for all frames')
    p.add_argument('--denoise', action='store_true')
    p.add_argument('--max-frames', type=int, default=2000)
    p.add_argument('--resume', action='store_true')
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    from PIL import Image
    source, sdk, output = a.source.resolve(), a.sdk_bin.resolve(), a.output.resolve()
    binary = sdk / 'MediaSDKTest.exe'
    if not source.is_file() or not binary.is_file() or not (sdk / 'models').is_dir():
        p.error('Source, SDK executable and models directory must exist')
    info = probe(source)
    videos = [s for s in info['streams'] if s['codec_type'] == 'video']
    if not videos:
        p.error('No source video stream')
    rate = Fraction(videos[0]['r_frame_rate'])
    if not 0 <= a.start < a.end <= float(info['format']['duration']):
        p.error('Invalid source interval')
    if a.sample is not None and not 1 / float(rate) <= a.sample <= a.end - a.start:
        p.error('Invalid analysis sampling interval')
    try:
        width, height = map(int, a.size.split('x'))
    except ValueError:
        p.error('Size must be WIDTHxHEIGHT')
    if width != height * 2 or height < 2 or width > 16384 or width % 2 or height % 2:
        p.error('Choose a bounded, even, 2:1 panorama size')
    first, last = round(a.start * rate), round(a.end * rate)
    if a.sample is None:
        indices = list(range(first, last + 1))
    else:
        import math
        indices = sorted({round((a.start + k * a.sample) * rate)
                          for k in range(math.ceil((a.end - a.start) / a.sample))})
    if not indices or len(indices) > a.max_frames:
        p.error('Frame budget exceeded; split the job or explicitly raise --max-frames')
    stat = source.stat()
    manifest = {'source': str(source), 'source_bytes': stat.st_size, 'source_mtime_ns': stat.st_mtime_ns,
                'sdk_executable_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                'sdk_bin': str(sdk), 'fps': str(rate), 'size': [width, height], 'indices': indices,
                'accessory': a.accessory, 'denoise': a.denoise, 'colorplus': False,
                'stitch': 'optflow', 'flowstate': True}
    print(json.dumps({'frames': len(indices), 'first': indices[0], 'last': indices[-1],
                      'fps': str(rate), 'execute': a.execute, 'output': str(output)}), flush=True)
    if not a.execute:
        return
    if output == source.parent:
        p.error('Use a separate frame output directory')
    output.mkdir(parents=True, exist_ok=True)
    mp = output / 'export-manifest.json'
    if mp.exists():
        if not a.resume or json.loads(mp.read_text()) != manifest:
            p.error('Resume requires identical source, binary, settings and interval')
    elif any(output.iterdir()):
        p.error('Output contains untracked files; use a new directory')
    else:
        with mp.open('x', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
    missing = []
    for n in indices:
        path = output / f'{n}.jpg'
        if path.exists():
            with Image.open(path) as im:
                if im.size != (width, height):
                    raise ValueError(f'Wrong cached frame dimensions: {path}')
                im.verify()
        else:
            missing.append(n)
    if shutil.disk_usage(output).free < len(missing) * width * height * 3:
        p.error('Insufficient conservative disk budget for export; choose a shorter interval')
    started = time.monotonic()
    # ponytail: batches bound Windows command-line length; existing files resume only with matching provenance.
    for offset in range(0, len(missing), 200):
        batch = missing[offset:offset + 200]
        cmd = [str(binary), '-inputs', str(source), '-image_sequence_dir', str(output),
               '-image_type', 'jpg', '-export_frame_index', '-'.join(map(str, batch)),
               '-output_size', a.size, '-stitch_type', 'optflow', '-enable_flowstate',
               '-camera_accessory_type', str(a.accessory), '-model_root_dir', str(sdk / 'models') + '/']
        if a.denoise:
            cmd.append('-enable_denoise')
        with (output / f'sdk-{batch[0]}-{time.time_ns()}.log').open('x', encoding='utf-8') as log:
            subprocess.run(cmd, cwd=sdk, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=900)
        for n in batch:
            with Image.open(output / f'{n}.jpg') as im:
                if im.size != (width, height):
                    raise ValueError('SDK produced incorrect dimensions')
                im.verify()
        print(f'Validated batch {offset // 200 + 1}', flush=True)
    after = source.stat()
    if (after.st_size, after.st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
        raise RuntimeError('Source changed')
    report = {'validated_frames': len(indices), 'new_frames': len(missing),
              'seconds': time.monotonic() - started, 'source_preserved': True}
    with (output / f'export-report-{time.time_ns()}.json').open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
