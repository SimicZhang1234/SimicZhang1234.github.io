"""Build a Pages artifact within its size budget while retaining original Git assets."""
from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / '_site'
LIMIT = 980_000_000
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

    # Continue into short archival clips if larger films alone cannot meet the
    # budget. Keep the same encoder settings and protected review bytes.
    candidates = [(name, path) for name, path in files
                  if name.startswith('demo/paladin/') and not name.startswith(PROTECTED)
                  and path.suffix.lower() == '.mp4' and path.stat().st_size > 300_000]
    candidates.sort(key=lambda row: row[1].stat().st_size, reverse=True)
    for name, path in candidates:
        if total <= LIMIT:
            break
        before = path.stat().st_size
        seconds, source_video = probe(path)
        # A capped encode bounds the historical film's contribution to the
        # artifact. Resolution, frame rate, audio and public URL are retained.
        # Make room for the new cave demo by adjusting only the deployment
        # copies of four older comparison reels. Source files and protected
        # review media retain their original bytes.
        if name.startswith('demo/paladin/assets/paladin-fivecast-repair-r') and before > 68_000_000:
            archive_ratio = 0.156395
        elif name in ('demo/paladin/assets/paladin-fivecast-r1.mp4', 'demo/paladin/assets/r5-repair-review-reel-r32.mp4', 'demo/paladin/assets/sovereign-full.mp4', 'demo/paladin/assets/champion-current.mp4', 'demo/paladin/assets/seraph-full.mp4', 'demo/paladin/assets/r5-seraph-native-wick-five-skills-r78.mp4'):
            # Re-encode these historical comparison copies inside the Pages build.
            archive_ratio = 0.156865
        else:
            archive_ratio = 0.32
        # Cap historical previews by their measured previous playback sizes.
        reviewed_archive_rates = {'demo/paladin/assets/paladin-fivecast-repair-r96.mp4': 0.115679, 'demo/paladin/assets/paladin-fivecast-repair-r112.mp4': 0.114108, 'demo/paladin/assets/paladin-fivecast-repair-r124.mp4': 0.115526, 'demo/paladin/assets/paladin-fivecast-r1.mp4': 0.108773, 'demo/paladin/assets/paladin-fivecast-repair-r52.mp4': 0.114857, 'demo/paladin/assets/champion-crowd.mp4': 0.09275, 'demo/paladin/assets/r5-repair-review-reel-r32.mp4': 0.109293, 'demo/paladin/assets/champion-execution.mp4': 0.081067, 'demo/paladin/assets/four-deaths.mp4': 0.152626, 'demo/paladin/assets/wound-death-progress.mp4': 0.089094, 'demo/paladin/assets/green-mobility.mp4': 0.086524, 'demo/paladin/assets/fivecast-receivedeath.mp4': 0.079729, 'demo/paladin/assets/outfit-mobility.mp4': 0.081872, 'demo/paladin/assets/green-combat.mp4': 0.110294, 'demo/paladin/assets/sovereign-light-fix.mp4': 0.095332, 'demo/paladin/assets/sovereign-face.mp4': 0.121012, 'demo/paladin/assets/sovereign-expression.mp4': 0.09368, 'demo/paladin/assets/r5-seraph-native-wick-five-skills-r78.mp4': 0.104877, 'demo/paladin/assets/outfit-crystal-mobility.mp4': 0.148327, 'demo/paladin/assets/sovereign-sky-check.mp4': 0.138438, 'demo/paladin/assets/death-chest.mp4': 0.141774, 'demo/paladin/assets/death-head.mp4': 0.151944, 'demo/paladin/assets/death-kneel.mp4': 0.157714, 'demo/paladin/assets/death-bisection.mp4': 0.150862, 'demo/paladin/assets/r5-champion-four-melee-contact-r64.mp4': 0.214482, 'demo/paladin/assets/lightblade-assassin-motion-r9.mp4': 0.209755, 'demo/paladin/assets/lightblade-assassin-lean-motion-r14.mp4': 0.205494}
        archive_ratio = reviewed_archive_rates.get(name, archive_ratio)
        cap = max(300_000, int(before * archive_ratio * 8 / seconds) - 96_000)
        video_quality = ['-crf', '27', '-maxrate', str(cap), '-bufsize', str(cap * 2)]
        measured_archive_caps = {'demo/paladin/assets/paladin-fivecast-repair-r96.mp4': 9028239, 'demo/paladin/assets/paladin-fivecast-repair-r112.mp4': 8881438, 'demo/paladin/assets/paladin-fivecast-repair-r124.mp4': 8808038, 'demo/paladin/assets/paladin-fivecast-repair-r52.mp4': 8294236, 'demo/paladin/assets/paladin-fivecast-r1.mp4': 8074035}
        if name in measured_archive_caps:
            cap = max(240_000, int(measured_archive_caps[name] * 8 / seconds) - 112_000)
            video_quality = ['-b:v', str(cap), '-maxrate', str(cap), '-bufsize', str(cap)]
        temporary = path.with_name(path.stem + '.pages-encode.mp4')
        subprocess.run([
            'ffmpeg', '-nostdin', '-v', 'error', '-threads', '2', '-i', str(path),
            '-map', '0:v:0', '-map', '0:a?', '-map_metadata', '0', '-map_chapters', '0',
            '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', *video_quality, '-pix_fmt', 'yuv420p',
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

    assert total <= LIMIT, f'Artifact still exceeds the 980 MB budget: {total}'
    for name, path in files:
        if name.startswith(PROTECTED):
            assert path.read_bytes() == (ROOT / name).read_bytes(), name
    assert (OUTPUT / 'demo/paladin/review-20261112.html').is_file()
    print(f'Pages artifact ready at {total / 1048576:.1f} MiB', flush=True)


if __name__ == '__main__':
    main()
