#!/usr/bin/env python3
import argparse
from pathlib import Path
from collections import defaultdict

import numpy as np
import soundfile as sf


def iter_wavs(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() == ".wav":
            yield p


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def db_to_linear(db):
    return 10 ** (db / 20.0)


def linear_to_db(x):
    return 20.0 * np.log10(x)


def to_mono(x):
    if x.ndim == 1:
        return x
    return np.mean(x, axis=1)


def rms(x, eps=1e-12):
    return float(np.sqrt(np.mean(np.square(x)) + eps))


def measure_file(path: Path):
    data, sr = sf.read(path, always_2d=False)
    if data.size == 0:
        return {"sr": sr, "peak": 0.0, "rms": 0.0, "status": "empty"}
    peak = float(np.max(np.abs(data)))
    if peak == 0.0:
        return {"sr": sr, "peak": 0.0, "rms": 0.0, "status": "silence"}
    mono = to_mono(data).astype(np.float64)
    return {"sr": sr, "peak": peak, "rms": rms(mono), "status": "ok"}


def normalize_one(in_path: Path, out_path: Path, target_rms_dbfs: float, peak_ceiling_dbfs: float, verbose: bool):
    data, sr = sf.read(in_path, always_2d=False)
    info = sf.info(in_path)

    if data.size == 0:
        ensure_parent(out_path)
        sf.write(out_path, data, sr, subtype=info.subtype, format=info.format)
        return "empty"

    peak_in = float(np.max(np.abs(data)))
    if peak_in == 0.0:
        ensure_parent(out_path)
        sf.write(out_path, data, sr, subtype=info.subtype, format=info.format)
        return "silence"

    mono = to_mono(data).astype(np.float64)
    rms_in = rms(mono)

    target_rms = db_to_linear(target_rms_dbfs)
    gain = target_rms / rms_in

    # Safety: ensure we do not exceed peak ceiling
    peak_ceiling = db_to_linear(peak_ceiling_dbfs)
    max_gain = peak_ceiling / peak_in
    if gain > max_gain:
        gain = max_gain  # still linear, just prevents clipping

    out = data * gain
    peak_out = float(np.max(np.abs(out)))
    rms_out = rms(to_mono(out).astype(np.float64))

    ensure_parent(out_path)
    sf.write(out_path, out, sr, subtype=info.subtype, format=info.format)

    if verbose:
        print(
            f"  {in_path.name}: gain {linear_to_db(gain):+.2f} dB, "
            f"RMS {linear_to_db(rms_in):.2f}->{linear_to_db(rms_out):.2f} dBFS, "
            f"peak {linear_to_db(peak_in):.2f}->{linear_to_db(peak_out):.2f} dBFS"
        )

    return "ok"


def main():
    ap = argparse.ArgumentParser(description="RMS normalize WAVs with a peak ceiling (no clipping, linear scaling).")
    ap.add_argument("root", help="Root folder to crawl")
    ap.add_argument("--target-rms-dbfs", type=float, default=-23.0, help="Desired RMS target (default -23 dBFS)")
    ap.add_argument("--peak-ceiling-dbfs", type=float, default=-1.0, help="Never exceed this peak (default -1 dBFS)")
    ap.add_argument("--dry-run", action="store_true", help="Only scan and report, do not write")
    ap.add_argument("--in-place", action="store_true", help="Overwrite files in place")
    ap.add_argument("--out-dir", default=None, help="Write to this folder, mirroring structure")
    ap.add_argument("--verbose", action="store_true", help="Print per-file stats")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        raise SystemExit(f"Root does not exist: {root}")

    # Crawl + counts
    dir_counts = defaultdict(int)
    wavs = []
    for p in iter_wavs(root):
        wavs.append(p)
        dir_counts[str(p.parent)] += 1

    print(f"Root: {root}")
    print("Directories covered (WAV count):")
    for d in sorted(dir_counts):
        print(f"  {d} : {dir_counts[d]}")
    print(f"Total WAV files: {len(wavs)}")

    if len(wavs) == 0:
        print("No WAV files found.")
        return

    # Measure all files and compute a target that is achievable without clipping for ALL files
    peak_ceiling = db_to_linear(args.peak_ceiling_dbfs)
    achievable_targets = []
    for p in wavs:
        m = measure_file(p)
        if m["status"] != "ok":
            continue
        # max RMS attainable without exceeding peak ceiling
        max_gain = peak_ceiling / m["peak"]
        achievable_targets.append(m["rms"] * max_gain)

    if achievable_targets:
        safe_target_rms = min(achievable_targets)
        safe_target_db = linear_to_db(safe_target_rms)
        chosen_target_db = min(args.target_rms_dbfs, safe_target_db)

        print(f"Requested target RMS: {args.target_rms_dbfs:.2f} dBFS")
        print(f"Max safe target RMS for ALL files (given peak ceiling {args.peak_ceiling_dbfs:.2f} dBFS): {safe_target_db:.2f} dBFS")
        print(f"Using target RMS: {chosen_target_db:.2f} dBFS (guaranteed no clipping)")

        args.target_rms_dbfs = chosen_target_db
    else:
        print("All files are silent/empty. Nothing to normalize.")
        return

    if args.dry_run:
        print("Dry run: no files written.")
        return

    if not args.in_place and not args.out_dir:
        raise SystemExit("Choose either --in-place or provide --out-dir")

    out_root = Path(args.out_dir).resolve() if args.out_dir else None

    for in_path in wavs:
        if args.in_place:
            out_path = in_path
        else:
            out_path = out_root / in_path.relative_to(root)

        normalize_one(
            in_path=in_path,
            out_path=out_path,
            target_rms_dbfs=args.target_rms_dbfs,
            peak_ceiling_dbfs=args.peak_ceiling_dbfs,
            verbose=args.verbose
        )

    print("Done.")


if __name__ == "__main__":
    main()
