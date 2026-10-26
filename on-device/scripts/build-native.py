"""Build pinned whisper.cpp for the simulator or a physical iOS device."""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "d1be6fde11ac6e0407606b4e42fe72d34add8037"
parser = argparse.ArgumentParser()
parser.add_argument("--device", action="store_true")
args = parser.parse_args()
source = ROOT / "vendor/whisper.cpp"


def run(*command):
    subprocess.run(command, check=True, cwd=ROOT)


if not source.exists():
    run("git", "clone", "--depth", "1", "--branch", "v1.9.5",
        "https://github.com/ggml-org/whisper.cpp.git", str(source))
actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
if actual != COMMIT:
    raise SystemExit(f"Unexpected engine revision: {actual}; expected {COMMIT}")
build = ROOT / ("build-device" if args.device else "build-simulator")
run("cmake", "-S", str(source), "-B", str(build), "-DCMAKE_SYSTEM_NAME=iOS",
    f"-DCMAKE_OSX_SYSROOT={'iphoneos' if args.device else 'iphonesimulator'}",
    "-DCMAKE_OSX_ARCHITECTURES=arm64", "-DCMAKE_OSX_DEPLOYMENT_TARGET=16.4",
    "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_SHARED_LIBS=OFF", "-DWHISPER_BUILD_EXAMPLES=OFF",
    "-DWHISPER_BUILD_TESTS=OFF", "-DWHISPER_BUILD_SERVER=OFF", "-DGGML_METAL=OFF",
    "-DGGML_OPENMP=OFF", "-DGGML_NATIVE=OFF", "-DGGML_CPU_ARM_ARCH=armv8.2-a+dotprod")
run("cmake", "--build", str(build), "--config", "Release", "-j", "6", "--target", "whisper")
libraries = ["src/libwhisper.a", "ggml/src/libggml.a", "ggml/src/libggml-base.a",
             "ggml/src/libggml-cpu.a", "ggml/src/ggml-blas/libggml-blas.a"]
run("libtool", "-static", "-o", str(build / "libquran-whisper.a"),
    *(str(build / library) for library in libraries))
if (ROOT / "models/ggml-model.bin").exists():
    run("xcodegen", "generate")
else:
    print("Native library ready. Prepare the model, then rerun to generate the Xcode project.")
