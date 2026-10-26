"""Package the existing native libraries/resources for the local Expo module."""
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
ios = root / 'expo-module/ios'
headers = root / 'build-framework-headers'
headers.mkdir(exist_ok=True)
for source in [root / 'vendor/whisper.cpp/include/whisper.h', *root.joinpath('vendor/whisper.cpp/ggml/include').glob('*.h')]:
    shutil.copy2(source, headers / source.name)
framework = root / 'build-framework/Whisper.xcframework'
if not framework.exists():
    subprocess.run(['xcodebuild', '-create-xcframework',
                    '-library', str(root / 'build-device/libquran-whisper.a'), '-headers', str(headers),
                    '-library', str(root / 'build-simulator/libquran-whisper.a'), '-headers', str(headers),
                    '-output', str(framework)], check=True)

def link(path, source):
    if not path.is_symlink() and not path.exists():
        path.symlink_to(source)

core = ios / 'Core'
if core.is_symlink(): core.unlink()
core.mkdir(exist_ok=True)
for source in (root / 'Native').iterdir():
    if source.suffix in ['.h', '.mm', '.swift']:
        link(core / source.name, source)
link(ios / 'Whisper.xcframework', '../../build-framework/Whisper.xcframework')
resources = ios / 'Resources'
resources.mkdir(exist_ok=True)
repo = root.parent
for name, source in {
    'ggml-model.bin': root / 'models/ggml-model.bin',
    'ggml-silero-v6.2.0.bin': root / 'models/ggml-silero-v6.2.0.bin',
    'quran_surah_1.json': repo / 'data/text/quran_surah_1.json',
    'surah_1_mishari.json': repo / 'data/timings/surah_1_mishari.json',
    'surah_1_husary.json': repo / 'data/timings/surah_1_husary.json',
    '001_16k.wav': repo / 'data/audio_cache/mishari/001_16k.wav',
    '001_husary_16k.wav': repo / 'data/audio_cache/husary/001_16k.wav',
}.items():
    if not source.exists(): raise SystemExit(f'Missing resource: {source}')
    link(resources / name, source)
print('Local Expo module prepared.')
