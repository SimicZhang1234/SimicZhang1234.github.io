"""Build a Pages artifact within its size budget while retaining original Git assets."""
from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / '_site'
LIMIT = 900 * 1024 * 1024
PROTECTED = 'demo/paladin/assets/review-'


def probe(path):
    info = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)
    ]))
    video = next(stream for stream in info['streams'] if stream['codec_type'] == 'video')
    return float(info['format']['duration']), video


def main():
    from PIL import Image

    if OUTPUT.exists():
        raise RuntimeError('The Pages destination must be a fresh directory.')
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    files = []
    for name in filter(None, paths):
        if name.startswith(('.github/', 'tools/')):
            continue
        source = ROOT / name
        if source.is_symlink() or not source.is_file():
            raise RuntimeError(f'Expected a regular tracked file at {name}')
        target = OUTPUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files.append((name, target))

    total = sum(path.stat().st_size for _, path in files)
    print(f'Original artifact size {total / 1048576:.1f} MiB', flush=True)
    # Published review clips keep their original bytes. Historical screenshots
    # and movies are optimized only in this disposable deployment directory.
    for name, path in files:
        if not name.startswith('demo/paladin/') or name.startswith(PROTECTED):
            continue
        if path.suffix.lower() not in {'.jpg', '.jpeg'} or path.stat().st_size < 300_000:
            continue
        old_size = path.stat().st_size
        temporary = path.with_name(path.name + '.optimized')
        with Image.open(path) as image:
            image.convert('RGB').save(temporary, 'JPEG', quality=85, optimize=True)
        new_size = temporary.stat().st_size
        if new_size < old_size:
            temporary.replace(path)
            total -= old_size - new_size
        else:
            temporary.unlink()

    candidates = [(name, path) for name, path in files
                  if name.startswith('demo/paladin/') and not name.startswith(PROTECTED)
                  and path.suffix.lower() == '.mp4' and path.stat().st_size > 8 * 1024 * 1024]
    candidates.sort(key=lambda row: row[1].stat().st_size, reverse=True)
    for name, path in candidates:
        if total <= LIMIT:
            break
        before = path.stat().st_size
        seconds, source_video = probe(path)
        # A capped encode bounds the historical film's contribution to the
        # artifact. Resolution, frame rate, audio and public URL are retained.
        cap = max(300_000, int(before * 0.40 * 8 / seconds) - 96_000)
        temporary = path.with_name(path.stem + '.pages-encode.mp4')
        subprocess.run([
            'ffmpeg', '-nostdin', '-v', 'error', '-threads', '2', '-i', str(path),
            '-map', '0:v:0', '-map', '0:a?', '-map_metadata', '0', '-map_chapters', '0',
            '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '26',
            '-maxrate', str(cap), '-bufsize', str(cap * 2), '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', str(temporary)
        ], check=True)
        actual_seconds, actual_video = probe(temporary)
        assert abs(seconds - actual_seconds) < 0.1, name
        for key in ('width', 'height', 'r_frame_rate'):
            assert actual_video[key] == source_video[key], (name, key)
        after = temporary.stat().st_size
        if after < before:
            temporary.replace(path)
            total -= before - after
            print(f'{name}: {before / 1048576:.1f} to {after / 1048576:.1f} MiB; artifact {total / 1048576:.1f} MiB', flush=True)
        else:
            temporary.unlink()

    assert total <= LIMIT, f'Artifact still exceeds the 900 MiB budget: {total}'
    for name, path in files:
        if name.startswith(PROTECTED):
            assert path.read_bytes() == (ROOT / name).read_bytes(), name
    assert (OUTPUT / 'demo/paladin/review-20261112.html').is_file()
    print(f'Pages artifact ready at {total / 1048576:.1f} MiB', flush=True)


if __name__ == '__main__':
    main()
