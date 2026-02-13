import sys
from pathlib import Path
import numpy as np
import soundfile as sf


def to_mono(data):
    # If already mono, return as-is
    if data.ndim == 1:
        return data
    # Average channels (L+R)/2
    return np.mean(data, axis=1)


def convert_one(in_path, out_path):
    data, sr = sf.read(in_path, always_2d=False)
    info = sf.info(in_path)

    mono = to_mono(data)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out_path, mono, sr, subtype=info.subtype, format=info.format)

    print(f"Converted: {in_path} → mono")


def main():
    if len(sys.argv) < 2:
        print("Usage: python wav_to_mono.py <wav file or folder> [--in-place | --out-dir DIR]")
        sys.exit(1)

    root = Path(sys.argv[1]).resolve()
    in_place = "--in-place" in sys.argv
    out_dir = None

    if "--out-dir" in sys.argv:
        idx = sys.argv.index("--out-dir")
        out_dir = Path(sys.argv[idx + 1]).resolve()

    if not in_place and out_dir is None:
        print("Choose either --in-place or --out-dir")
        sys.exit(1)

    if root.is_file():
        if root.suffix.lower() != ".wav":
            print("Not a WAV file")
            sys.exit(1)

        out_path = root if in_place else out_dir / root.name
        convert_one(root, out_path)
        return

    if root.is_dir():
        for wav in root.rglob("*.wav"):
            out_path = wav if in_place else out_dir / wav.relative_to(root)
            convert_one(wav, out_path)
        return

    print("Invalid path")


if __name__ == "__main__":
    main()
