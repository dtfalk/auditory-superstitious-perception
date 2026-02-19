#!/usr/bin/env python3
"""
Compare audio_stimuli/ (new) vs audio_stimuli_old/ (old) to summarize
what changed between the two stimulus sets.

Outputs a detailed comparison to console and saves to
  compare_stimuli_output.txt
"""

import csv
from pathlib import Path
from io import StringIO

import numpy as np
import soundfile as sf

SCRIPT_DIR = Path(__file__).resolve().parent
OLD_ROOT = SCRIPT_DIR / "audio_stimuli_old"
NEW_ROOT = SCRIPT_DIR / "audio_stimuli"
LOG_FILE = SCRIPT_DIR / "compare_stimuli_output.txt"

SUBFOLDERS = [
    "examples/targets",
    "examples/distractors",
    "full_sentence/targets",
    "full_sentence/distractors",
    "imagined_sentence/targets",
    "imagined_sentence/distractors",
]

_buf = StringIO()

def log(msg=""):
    print(msg)
    _buf.write(msg + "\n")

def flush_log():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(_buf.getvalue())
    print(f"\n[LOG SAVED] {LOG_FILE}")


def get_stim_nums(folder: Path):
    """Return set of integer stimulus numbers from .wav filenames in folder."""
    nums = set()
    if not folder.exists():
        return nums
    for f in folder.glob("*.wav"):
        try:
            nums.add(int(f.stem))
        except ValueError:
            pass
    return nums


def load_corr_csv(path: Path):
    """Return dict {stimulus_number: r_score} from a correlation CSV."""
    d = {}
    if not path.exists():
        return d
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                d[int(row["stimulus_number"])] = float(row["r_score"])
            except (ValueError, KeyError):
                pass
    return d


def describe_r_scores(label, nums, r_dict):
    """Print summary stats for a set of stimulus numbers using r_dict."""
    rs = [r_dict[n] for n in nums if n in r_dict]
    if not rs:
        log(f"  {label}: no r_score data available")
        return
    log(f"  {label} (n={len(rs)}): mean={np.mean(rs):.10f}  std={np.std(rs):.10f}  "
        f"min={np.min(rs):.10f}  max={np.max(rs):.10f}")


def main():
    log("=" * 80)
    log("  OLD vs NEW AUDIO STIMULI COMPARISON")
    log("=" * 80)

    # ── Load correlation lookups ──
    old_high = load_corr_csv(OLD_ROOT / "correlation_csvs" / "high_correlation_stimuli.csv")
    old_low  = load_corr_csv(OLD_ROOT / "correlation_csvs" / "low_correlation_stimuli.csv")
    new_high = load_corr_csv(NEW_ROOT / "correlation_csvs" / "high_correlation_stimuli.csv")
    new_low  = load_corr_csv(NEW_ROOT / "correlation_csvs" / "low_correlation_stimuli.csv")

    # Merge into a single lookup per set for convenience
    old_all = {**old_high, **old_low}
    new_all = {**new_high, **new_low}

    # ── Per-subfolder comparison ──
    for sub in SUBFOLDERS:
        log()
        log("-" * 70)
        log(f"  {sub}")
        log("-" * 70)

        old_nums = get_stim_nums(OLD_ROOT / sub)
        new_nums = get_stim_nums(NEW_ROOT / sub)

        log(f"  OLD count: {len(old_nums)}")
        log(f"  NEW count: {len(new_nums)}")

        shared   = old_nums & new_nums
        removed  = old_nums - new_nums
        added    = new_nums - old_nums

        log(f"  Shared (in both)   : {len(shared)}")
        log(f"  Removed (old only) : {len(removed)}")
        log(f"  Added   (new only) : {len(added)}")

        pct_retained = (len(shared) / len(old_nums) * 100) if old_nums else 0
        log(f"  Retention rate     : {pct_retained:.1f}%")

        if shared:
            log(f"  Shared stimuli     : {sorted(shared)}")
        if removed:
            log(f"  Removed stimuli    : {sorted(removed)}")
        if added:
            log(f"  Added stimuli      : {sorted(added)}")

        # r-score summaries
        is_target = "targets" in sub
        old_r = old_high if is_target else old_low
        new_r = new_high if is_target else new_low

        log()
        describe_r_scores("OLD r_scores", old_nums, old_r)
        describe_r_scores("NEW r_scores", new_nums, new_r)

        # Compare r-score distributions of shared stimuli across old/new lookups
        if shared:
            old_shared_r = sorted([old_r.get(n, new_r.get(n, float("nan"))) for n in shared])
            new_shared_r = sorted([new_r.get(n, old_r.get(n, float("nan"))) for n in shared])

    # ── Global summary ──
    log()
    log("=" * 80)
    log("  GLOBAL SUMMARY")
    log("=" * 80)

    all_old_targets = set()
    all_new_targets = set()
    all_old_dists   = set()
    all_new_dists   = set()

    for sub in SUBFOLDERS:
        old_nums = get_stim_nums(OLD_ROOT / sub)
        new_nums = get_stim_nums(NEW_ROOT / sub)
        if "targets" in sub:
            all_old_targets |= old_nums
            all_new_targets |= new_nums
        else:
            all_old_dists |= old_nums
            all_new_dists |= new_nums

    log(f"\n  TARGETS (across all subfolders):")
    log(f"    OLD total unique : {len(all_old_targets)}")
    log(f"    NEW total unique : {len(all_new_targets)}")
    shared_t = all_old_targets & all_new_targets
    log(f"    Shared           : {len(shared_t)}")
    log(f"    Removed          : {len(all_old_targets - all_new_targets)}")
    log(f"    Added            : {len(all_new_targets - all_old_targets)}")
    pct_t = (len(shared_t) / len(all_old_targets) * 100) if all_old_targets else 0
    log(f"    Retention rate   : {pct_t:.1f}%")

    log(f"\n  DISTRACTORS (across all subfolders):")
    log(f"    OLD total unique : {len(all_old_dists)}")
    log(f"    NEW total unique : {len(all_new_dists)}")
    shared_d = all_old_dists & all_new_dists
    log(f"    Shared           : {len(shared_d)}")
    log(f"    Removed          : {len(all_old_dists - all_new_dists)}")
    log(f"    Added            : {len(all_new_dists - all_old_dists)}")
    pct_d = (len(shared_d) / len(all_old_dists) * 100) if all_old_dists else 0
    log(f"    Retention rate   : {pct_d:.1f}%")

    # ── r-score range comparison ──
    log()
    log("-" * 70)
    log("  r-score distribution comparison (full pool, all 153 per type)")
    log("-" * 70)

    log("\n  HIGH CORRELATION (targets):")
    describe_r_scores("OLD", set(old_high.keys()), old_high)
    describe_r_scores("NEW", set(new_high.keys()), new_high)

    log("\n  LOW CORRELATION (distractors):")
    describe_r_scores("OLD", set(old_low.keys()), old_low)
    describe_r_scores("NEW", set(new_low.keys()), new_low)

    # ── Audio property comparison (spot check) ──
    log()
    log("-" * 70)
    log("  Audio property spot-check (first file from each new subfolder)")
    log("-" * 70)
    for sub in SUBFOLDERS:
        d = NEW_ROOT / sub
        wavs = sorted(d.glob("*.wav"))
        if wavs:
            info = sf.info(str(wavs[0]))
            log(f"  {sub}/{wavs[0].name}: sr={int(info.samplerate)} ch={info.channels} "
                f"frames={info.frames} subtype={info.subtype}")

    log()
    log("=" * 80)
    log("  COMPARISON COMPLETE")
    log("=" * 80)

    flush_log()


if __name__ == "__main__":
    main()
