"""Fetch one pinned public checkpoint, then use the upstream GGML converter."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REVISION = "5c3c53fdf9272c4f6ee0bee09a1e5a4a615ee25c"
MODEL = "tarteel-ai/whisper-base-ar-quran"
VAD_REVISION = "9ffd54a1e1ee413ddf265af9913beaf518d1639b"
VAD_SHA256 = "2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987"


def fetch(url, path):
    if not path.exists():
        temporary = path.with_suffix(path.suffix + ".partial")
        urllib.request.urlretrieve(url, temporary)
        temporary.replace(path)


directory = ROOT / "models/hf"
directory.mkdir(parents=True, exist_ok=True)
vad = ROOT / "models/ggml-silero-v6.2.0.bin"
fetch(f"https://huggingface.co/ggml-org/whisper-vad/resolve/{VAD_REVISION}/{vad.name}", vad)
for name in ["pytorch_model.bin", "config.json", "vocab.json", "added_tokens.json",
             "tokenizer_config.json", "special_tokens_map.json", "merges.txt",
             "preprocessor_config.json"]:
    fetch(f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{name}", directory / name)
assets = ROOT / "models/openai/whisper/assets"
assets.mkdir(parents=True, exist_ok=True)
fetch("https://raw.githubusercontent.com/openai/whisper/v20250625/whisper/assets/mel_filters.npz",
      assets / "mel_filters.npz")
for path, expected in [
    (vad, VAD_SHA256),
    (directory / "pytorch_model.bin", "ec75894993a4570a237b2b1c19fd8a448f1e8f6e083cfab699574f7be53874fa"),
    (assets / "mel_filters.npz", "7450ae70723a5ef9d341e3cee628c7cb0177f36ce42c44b7ed2bf3325f0f6d4c")
]:
    with path.open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != expected:
            raise SystemExit(f"Checksum mismatch: {path}")
# The upstream converter uses generation max_length (1024 here) as the model's
# decoder context; the actual positional tensor and max_target_positions are 448.
conversion = ROOT / "models/conversion"
conversion.mkdir(exist_ok=True)
for source in directory.iterdir():
    target = conversion / source.name
    if source.name != "config.json" and not target.exists():
        target.symlink_to(source)
config = json.loads((directory / "config.json").read_text())
config["max_length"] = config["max_target_positions"]
(conversion / "config.json").write_text(json.dumps(config))
subprocess.run([sys.executable, str(ROOT / "vendor/whisper.cpp/models/convert-h5-to-ggml.py"),
                str(conversion), str(ROOT / "models/openai"), str(ROOT / "models")], check=True)
output = ROOT / "models/ggml-model.bin"
with output.open("rb") as handle:
    digest = hashlib.file_digest(handle, "sha256").hexdigest()
manifest = {"model": MODEL, "revision": REVISION, "format": "ggml-f16",
            "bytes": output.stat().st_size, "sha256": digest,
            "engine_commit": "d1be6fde11ac6e0407606b4e42fe72d34add8037",
            "vad": {"model": "ggml-org/whisper-vad", "revision": VAD_REVISION,
                    "file": vad.name, "sha256": VAD_SHA256}}
(ROOT / "model-lock.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
