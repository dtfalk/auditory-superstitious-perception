import sys
from pathlib import Path
import soundfile as sf


def trim_tail_ms_inplace(path, trim_ms):
    data, sr = sf.read(path, always_2d=False)
    info = sf.info(path)

    trim_samples = int(round((trim_ms / 1000.0) * sr))

    if trim_samples <= 0:
        raise ValueError("trim_ms must be > 0")

    if data.shape[0] <= trim_samples:
        raise ValueError("Trim duration longer than file length")

    trimmed = data[:-trim_samples]

    # Write back to SAME file
    sf.write(path, trimmed, sr, subtype=info.subtype, format=info.format)

    print(f"Trimmed {trim_ms} ms from end (in place)")
    print(f"File: {path}")
    print(f"Samples removed: {trim_samples}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python trim_tail_ms_inplace.py <file.wav> <trim_ms>")
        sys.exit(1)

    path = Path(sys.argv[1]).resolve()
    trim_ms = float(sys.argv[2])

    if not path.exists():
        print("File does not exist")
        sys.exit(1)

    trim_tail_ms_inplace(path, trim_ms)


if __name__ == "__main__":
    main()
