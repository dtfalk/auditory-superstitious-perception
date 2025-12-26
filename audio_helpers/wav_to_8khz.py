import sys
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


TARGET_SR = 8000


def resample_audio(data, sr, target_sr):
    if sr == target_sr:
        return data

    # Polyphase resampling (high quality, efficient)
    gcd = np.gcd(sr, target_sr)
    up = target_sr // gcd
    down = sr // gcd

    if data.ndim == 1:
        return resample_poly(data, up, down)
    else:
        # Resample each channel independently
        return np.vstack([
            resample_poly(data[:, ch], up, down)
            for ch in range(data.shape[1])
        ]).T


def convert_one(in_path, out_path):
    data, sr = sf.read(in_path, always_2d=False)
    info = sf.info(in_path)

    out = resample_audio(data, sr, TARGET_SR)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out_path, out, TARGET_SR, subtype=info.subtype, format=info.format)

    print(f"Resampled to 8 kHz: {in_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python wav_to_8khz.py <wav file or folder> [--in-place | --out-dir DIR]")
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
