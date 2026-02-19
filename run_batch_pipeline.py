#!/usr/bin/env python3
"""
==========================================================================
  Batch Stimuli Preparation Pipeline
==========================================================================
  Iterates over copy_folder_{N} directories and produces a corresponding
  audio_stimuli_{N} output for each one.

  For every folder the full pipeline is executed:
    1. Read pearson_scores.csv → create high / low correlation CSVs
    2. Verify copy_folder_{N}/targets match top 153 by raw pearson score
    3. Verify copy_folder_{N}/distractors match bottom 153 by |pearson|
    4. Validate audio properties (mono, 8 kHz, PCM_16, frame count)
    5. Split into full_sentence / imagined_sentence / examples
    6. Summary statistics
    7. RMS-normalise every WAV in the output folder
    8. Final gain verification

  Usage:
      python run_batch_pipeline.py                   # auto-discover all copy_folder_*
      python run_batch_pipeline.py 1 2 5             # only process these numbers
      python run_batch_pipeline.py --dry-run          # preview without writing
==========================================================================
"""

import argparse
import csv
import math
import os
import random
import re
import shutil
import sys
import wave
from collections import defaultdict
from datetime import datetime
from io import StringIO
from pathlib import Path
from statistics import median

import numpy as np
import soundfile as sf


# ──────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
POTENTIAL_ROOT = PROJECT_ROOT / "potential_stimuli"

# Reference wall.wav — used for frame-count validation only
WALL_WAV = PROJECT_ROOT / "audio_stimuli" / "wall.wav"

# Split parameters (must sum to 153 per pool)
EXAMPLES_PER_POOL = 3
MAIN_PER_SUBFOLDER = 75
TOP_N = 153
assert EXAMPLES_PER_POOL + 2 * MAIN_PER_SUBFOLDER == TOP_N

# Optimiser knobs
INIT_METHOD = "snake"
ITERATIONS = 200_000
SEED_HIGH = 42
SEED_LOW = 43

# RMS normalisation defaults
TARGET_RMS_DBFS = -23.0
PEAK_CEILING_DBFS = -1.0


# ══════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════
class PipelineLogger:
    """Tee every message to both stdout and an in-memory buffer."""

    def __init__(self):
        self._buf = StringIO()

    def log(self, msg=""):
        print(msg)
        self._buf.write(msg + "\n")

    def flush_to(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._buf.getvalue())
        print(f"\n[LOG SAVED] {path}")

    def append_to(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n")
            f.write(self._buf.getvalue())
        print(f"\n[LOG APPENDED] {path}")


# ══════════════════════════════════════════════════════════════════════════
# STEP 1 — Create high/low correlation CSVs
# ══════════════════════════════════════════════════════════════════════════
def step1_create_correlation_csvs(pearson_csv: Path, corr_csv_dir: Path, L):
    L.log("=" * 80)
    L.log("STEP 1: Create high_correlation_stimuli.csv and low_correlation_stimuli.csv")
    L.log("=" * 80)
    L.log(f"Source CSV : {pearson_csv}")
    L.log(f"Output dir : {corr_csv_dir}")
    L.log()

    rows = []
    with open(pearson_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    L.log(f"Total rows in pearson_scores.csv: {len(rows)}")

    parsed = []
    for row in rows:
        try:
            chunk_num = int(row["chunk_number"])
            r_score = float(row["r_score"])
            parsed.append((chunk_num, r_score))
        except (ValueError, KeyError):
            continue
    L.log(f"Successfully parsed rows: {len(parsed)}")

    # HIGH: top 153 by raw r_score (descending)
    sorted_by_raw = sorted(parsed, key=lambda x: x[1], reverse=True)
    high_153 = sorted_by_raw[:TOP_N]

    high_csv_path = corr_csv_dir / "high_correlation_stimuli.csv"
    with open(high_csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stimulus_number", "r_score"])
        for chunk_num, r in high_153:
            w.writerow([chunk_num, r])
    L.log(f"\nWrote {high_csv_path.name}  ({len(high_153)} rows)")
    L.log(f"  Highest r_score : {high_153[0][1]}")
    L.log(f"  Lowest  r_score : {high_153[-1][1]}")
    L.log(f"  Chunk #s (first 10): {[h[0] for h in high_153[:10]]}")

    # LOW: bottom 153 by abs(r_score) (ascending)
    sorted_by_abs = sorted(parsed, key=lambda x: abs(x[1]))
    low_153 = sorted_by_abs[:TOP_N]

    low_csv_path = corr_csv_dir / "low_correlation_stimuli.csv"
    with open(low_csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stimulus_number", "r_score"])
        for chunk_num, r in low_153:
            w.writerow([chunk_num, r])
    L.log(f"\nWrote {low_csv_path.name}  ({len(low_153)} rows)")
    L.log(f"  Smallest |r_score| : {abs(low_153[0][1])}")
    L.log(f"  Largest  |r_score| : {abs(low_153[-1][1])}")
    L.log(f"  Chunk #s (first 10): {[l[0] for l in low_153[:10]]}")

    L.log("\n[STEP 1 COMPLETE]\n")
    return high_153, low_153


# ══════════════════════════════════════════════════════════════════════════
# STEP 2 — Verify targets
# ══════════════════════════════════════════════════════════════════════════
def step2_verify_targets(high_153, targets_dir: Path, L):
    L.log("=" * 80)
    L.log("STEP 2: Verify targets/ contains exactly the top 153 stimuli")
    L.log("=" * 80)

    expected_nums = {h[0] for h in high_153}
    actual_files = list(targets_dir.glob("*.wav"))
    actual_nums = set()
    for f in actual_files:
        try:
            num = int(f.stem.split("_")[1])
            actual_nums.add(num)
        except (IndexError, ValueError):
            L.log(f"  WARNING: Could not parse filename: {f.name}")

    L.log(f"Expected target count : {len(expected_nums)}")
    L.log(f"Actual   target count : {len(actual_nums)}")

    missing = expected_nums - actual_nums
    extra = actual_nums - expected_nums

    if missing:
        L.log(f"\n  MISSING from targets/ ({len(missing)}): {sorted(missing)}")
    if extra:
        L.log(f"\n  EXTRA in targets/ ({len(extra)}): {sorted(extra)}")

    match = not missing and not extra and len(actual_nums) == TOP_N
    if match:
        L.log("\n  ** CONFIRMED: targets/ contains exactly the top 153 high-correlation stimuli **")
    else:
        L.log("\n  ** MISMATCH DETECTED — see details above **")

    L.log("\n[STEP 2 COMPLETE]\n")
    return match


# ══════════════════════════════════════════════════════════════════════════
# STEP 3 — Verify distractors
# ══════════════════════════════════════════════════════════════════════════
def step3_verify_distractors(low_153, distractors_dir: Path, L):
    L.log("=" * 80)
    L.log("STEP 3: Verify distractors/ contains exactly the bottom 153 stimuli")
    L.log("=" * 80)

    expected_nums = {l[0] for l in low_153}
    actual_files = list(distractors_dir.glob("*.wav"))
    actual_nums = set()
    for f in actual_files:
        try:
            num = int(f.stem.split("_")[1])
            actual_nums.add(num)
        except (IndexError, ValueError):
            L.log(f"  WARNING: Could not parse filename: {f.name}")

    L.log(f"Expected distractor count : {len(expected_nums)}")
    L.log(f"Actual   distractor count : {len(actual_nums)}")

    missing = expected_nums - actual_nums
    extra = actual_nums - expected_nums

    if missing:
        L.log(f"\n  MISSING from distractors/ ({len(missing)}): {sorted(missing)}")
    if extra:
        L.log(f"\n  EXTRA in distractors/ ({len(extra)}): {sorted(extra)}")

    match = not missing and not extra and len(actual_nums) == TOP_N
    if match:
        L.log("\n  ** CONFIRMED: distractors/ contains exactly the bottom 153 low-correlation stimuli **")
    else:
        L.log("\n  ** MISMATCH DETECTED — see details above **")

    L.log("\n[STEP 3 COMPLETE]\n")
    return match


# ══════════════════════════════════════════════════════════════════════════
# STEP 4 — Validate audio properties
# ══════════════════════════════════════════════════════════════════════════
def step4_validate_audio(targets_dir: Path, distractors_dir: Path, wall_wav: Path, L):
    L.log("=" * 80)
    L.log("STEP 4: Validate audio properties (mono, 8 kHz, PCM_16, frame count)")
    L.log("=" * 80)

    wall_info = sf.info(str(wall_wav))
    ref_frames = wall_info.frames
    ref_sr = int(wall_info.samplerate)

    L.log(f"\nReference file: {wall_wav.name}")
    L.log(f"  Sample rate : {ref_sr} Hz")
    L.log(f"  Channels    : {wall_info.channels}")
    L.log(f"  Frames      : {ref_frames}")
    L.log(f"  Subtype     : {wall_info.subtype}")
    L.log(f"  Duration    : {ref_frames / ref_sr:.4f} s")
    L.log()

    all_ok = True
    issues = []

    for label, folder in [("targets", targets_dir), ("distractors", distractors_dir)]:
        wavs = sorted(folder.glob("*.wav"))
        L.log(f"Checking {label}/ — {len(wavs)} files")
        folder_ok = True
        for wav in wavs:
            info = sf.info(str(wav))
            problems = []
            if info.channels != 1:
                problems.append(f"channels={info.channels} (expected 1)")
            if int(info.samplerate) != 8000:
                problems.append(f"samplerate={int(info.samplerate)} (expected 8000)")
            if info.subtype != "PCM_16":
                problems.append(f"subtype={info.subtype} (expected PCM_16)")
            if info.frames != ref_frames:
                problems.append(f"frames={info.frames} (expected {ref_frames})")
            if problems:
                msg = f"  FAIL  {wav.name}: {'; '.join(problems)}"
                L.log(msg)
                issues.append(msg)
                folder_ok = False
                all_ok = False

        if folder_ok:
            L.log(f"  All {len(wavs)} files in {label}/ PASSED")
            L.log(f"    Channels   : 1 (mono)")
            L.log(f"    Sample rate: 8000 Hz")
            L.log(f"    Subtype    : PCM_16 (16-bit)")
            L.log(f"    Frames     : {ref_frames} (matches wall.wav)")
        L.log()

    if all_ok:
        L.log(f"  ** CONFIRMED: All 306 stimuli files are mono, 8 kHz, 16-bit PCM, "
              f"and have {ref_frames} frames (matching wall.wav) **")
    else:
        L.log(f"  ** {len(issues)} ISSUE(S) FOUND — see details above **")

    L.log("\n[STEP 4 COMPLETE]\n")
    return all_ok


# ══════════════════════════════════════════════════════════════════════════
# STEP 5 — Split into final folder structure  (with optimiser)
# ══════════════════════════════════════════════════════════════════════════
def stats_tuple(rs):
    mu = sum(rs) / len(rs)
    return (min(rs), max(rs), float(mu), float(median(rs)))


def split_cost(rs_a, rs_b):
    a = stats_tuple(rs_a)
    b = stats_tuple(rs_b)
    return sum((x - y) ** 2 for x, y in zip(a, b))


def init_partition(items, target_size, init_method="snake", seed=0):
    if len(items) != 2 * target_size:
        raise ValueError(f"Expected {2 * target_size} items, got {len(items)}")
    idx_sorted = sorted(range(len(items)), key=lambda i: items[i][1])

    if init_method == "random":
        rng = random.Random(seed)
        idxs = list(range(len(items)))
        rng.shuffle(idxs)
        A = set(idxs[:target_size])
        B = set(idxs[target_size:])
        return A, B

    A, B = set(), set()
    pairs = [idx_sorted[i:i + 2] for i in range(0, len(idx_sorted), 2)]
    for k, pair in enumerate(pairs):
        if len(pair) < 2:
            A.add(pair[0])
            continue
        if k % 2 == 0:
            A.add(pair[0]); B.add(pair[1])
        else:
            A.add(pair[1]); B.add(pair[0])

    if len(A) != target_size or len(B) != target_size:
        raise RuntimeError(f"Init sizes A={len(A)} B={len(B)} (expected {target_size})")
    return A, B


def optimize_two_groups(items, target_size=75, iterations=200_000,
                        seed=0, init_method="snake"):
    rng = random.Random(seed)
    rs = [r for _, r in items]
    A, B = init_partition(items, target_size, init_method=init_method, seed=seed)
    current_cost = split_cost([rs[i] for i in A], [rs[i] for i in B])
    best_cost = current_cost
    bestA, bestB = set(A), set(B)

    T0 = 1.0
    for it in range(iterations):
        T = T0 * (1.0 - (it / iterations))
        i = rng.choice(tuple(A))
        j = rng.choice(tuple(B))

        A2, B2 = set(A), set(B)
        A2.remove(i); B2.remove(j)
        A2.add(j); B2.add(i)

        new_cost = split_cost([rs[k] for k in A2], [rs[k] for k in B2])
        if new_cost < current_cost:
            accept = True
        else:
            accept = rng.random() < math.exp((current_cost - new_cost) / (T + 1e-12))

        if accept:
            A, B = A2, B2
            current_cost = new_cost
            if current_cost < best_cost:
                best_cost = current_cost
                bestA, bestB = set(A), set(B)

    groupA = [items[i] for i in sorted(bestA)]
    groupB = [items[i] for i in sorted(bestB)]
    return groupA, groupB


def step5_split_and_copy(high_153, low_153,
                         targets_dir: Path, distractors_dir: Path,
                         corr_csv_dir: Path, out_root: Path, L):
    L.log("=" * 80)
    L.log("STEP 5: Split 153 targets + 153 distractors into final folder structure")
    L.log("=" * 80)
    L.log(f"  Output root       : {out_root}")
    L.log(f"  Examples per pool  : {EXAMPLES_PER_POOL}")
    L.log(f"  Main per subfolder : {MAIN_PER_SUBFOLDER}")
    L.log(f"  Optimiser iters    : {ITERATIONS}")
    L.log(f"  Init method        : {INIT_METHOD}")
    L.log()

    for sub in [
        "examples/targets", "examples/distractors",
        "full_sentence/targets", "full_sentence/distractors",
        "imagined_sentence/targets", "imagined_sentence/distractors",
        "correlation_csvs",
    ]:
        (out_root / sub).mkdir(parents=True, exist_ok=True)

    rng = random.Random(99)

    high_nums = [h[0] for h in high_153]
    low_nums  = [l[0] for l in low_153]

    high_example_nums = set(rng.sample(high_nums, EXAMPLES_PER_POOL))
    low_example_nums  = set(rng.sample(low_nums,  EXAMPLES_PER_POOL))

    L.log(f"Selected example targets     : {sorted(high_example_nums)}")
    L.log(f"Selected example distractors : {sorted(low_example_nums)}")

    high_dict = {h[0]: h[1] for h in high_153}
    low_dict  = {l[0]: l[1] for l in low_153}

    for num in sorted(high_example_nums):
        src = targets_dir / f"chunk_{num}.wav"
        dst = out_root / "examples" / "targets" / f"{num}.wav"
        shutil.copy2(src, dst)
        L.log(f"  Copied example target: chunk_{num}.wav -> examples/targets/{num}.wav  (r={high_dict[num]:.10f})")

    for num in sorted(low_example_nums):
        src = distractors_dir / f"chunk_{num}.wav"
        dst = out_root / "examples" / "distractors" / f"{num}.wav"
        shutil.copy2(src, dst)
        L.log(f"  Copied example distractor: chunk_{num}.wav -> examples/distractors/{num}.wav  (r={low_dict[num]:.15e})")

    high_remaining = [(n, r) for n, r in high_153 if n not in high_example_nums]
    low_remaining  = [(n, r) for n, r in low_153  if n not in low_example_nums]

    L.log(f"\nHigh remaining for split: {len(high_remaining)}  (expected {MAIN_PER_SUBFOLDER * 2})")
    L.log(f"Low  remaining for split: {len(low_remaining)}  (expected {MAIN_PER_SUBFOLDER * 2})")

    if len(high_remaining) != MAIN_PER_SUBFOLDER * 2:
        L.log(f"  ERROR: Expected {MAIN_PER_SUBFOLDER * 2} high items, got {len(high_remaining)}")
        return None
    if len(low_remaining) != MAIN_PER_SUBFOLDER * 2:
        L.log(f"  ERROR: Expected {MAIN_PER_SUBFOLDER * 2} low items, got {len(low_remaining)}")
        return None

    L.log(f"\nOptimising high-correlation split (full_sentence vs imagined_sentence targets)...")
    L.log(f"  Iterations: {ITERATIONS}, Seed: {SEED_HIGH}, Init: {INIT_METHOD}")
    high_A, high_B = optimize_two_groups(
        high_remaining, target_size=MAIN_PER_SUBFOLDER,
        iterations=ITERATIONS, seed=SEED_HIGH, init_method=INIT_METHOD
    )
    L.log("  Done.")

    L.log(f"\nOptimising low-correlation split (full_sentence vs imagined_sentence distractors)...")
    L.log(f"  Iterations: {ITERATIONS}, Seed: {SEED_LOW}, Init: {INIT_METHOD}")
    low_A, low_B = optimize_two_groups(
        low_remaining, target_size=MAIN_PER_SUBFOLDER,
        iterations=ITERATIONS, seed=SEED_LOW, init_method=INIT_METHOD
    )
    L.log("  Done.")

    copy_map = [
        ("full_sentence/targets",         targets_dir,     high_A),
        ("imagined_sentence/targets",     targets_dir,     high_B),
        ("full_sentence/distractors",     distractors_dir, low_A),
        ("imagined_sentence/distractors", distractors_dir, low_B),
    ]

    for subfolder, src_dir, group in copy_map:
        dest_dir = out_root / subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)
        L.log(f"\nCopying {len(group)} files -> {subfolder}/")
        for stim_num, r_score in group:
            src = src_dir / f"chunk_{stim_num}.wav"
            dst = dest_dir / f"{stim_num}.wav"
            shutil.copy2(src, dst)
        L.log(f"  Copied {len(group)} files to {subfolder}/")

    for csv_name in ["high_correlation_stimuli.csv", "low_correlation_stimuli.csv"]:
        src = corr_csv_dir / csv_name
        dst = out_root / "correlation_csvs" / csv_name
        shutil.copy2(src, dst)
        L.log(f"\nCopied {csv_name} -> {out_root.name}/correlation_csvs/")

    L.log("\n[STEP 5 COMPLETE]\n")

    return {
        "full_sentence_targets": high_A,
        "imagined_sentence_targets": high_B,
        "full_sentence_distractors": low_A,
        "imagined_sentence_distractors": low_B,
        "examples_targets": [(n, high_dict[n]) for n in sorted(high_example_nums)],
        "examples_distractors": [(n, low_dict[n]) for n in sorted(low_example_nums)],
    }


# ══════════════════════════════════════════════════════════════════════════
# STEP 6 — Summary statistics
# ══════════════════════════════════════════════════════════════════════════
def print_summary_stats(label, group, L):
    rs = [r for _, r in group]
    n = len(rs)
    if n == 0:
        L.log(f"Summary Statistics for {label} (n = 0) — EMPTY")
        return

    mu = np.mean(rs)
    sd = np.std(rs)
    mn = np.min(rs)
    mx = np.max(rs)
    rng_val = mx - mn
    med = float(np.median(rs))

    L.log(f"Summary Statistics for {label} condition (n = {n})")
    L.log("=" * 60)
    L.log(f"  Mean   : {mu}")
    L.log(f"  Std    : {sd}")
    L.log(f"  Range  : {rng_val}")
    L.log(f"  Max    : {mx}")
    L.log(f"  Min    : {mn}")
    L.log(f"  Median : {med}")
    L.log(f"  Stimuli: {sorted([s for s, _ in group])}")
    L.log()


def step6_statistics(groups, out_root: Path, L):
    L.log("=" * 80)
    L.log("STEP 6: Summary Statistics for All Conditions")
    L.log("=" * 80)
    L.log()

    condition_labels = [
        ("full_sentence-targets",         "full_sentence_targets"),
        ("full_sentence-distractors",     "full_sentence_distractors"),
        ("imagined_sentence-targets",     "imagined_sentence_targets"),
        ("imagined_sentence-distractors", "imagined_sentence_distractors"),
        ("examples-targets",              "examples_targets"),
        ("examples-distractors",          "examples_distractors"),
    ]
    for label, key in condition_labels:
        print_summary_stats(label, groups[key], L)

    all_targets_ex_excl = groups["full_sentence_targets"] + groups["imagined_sentence_targets"]
    all_dist_ex_excl    = groups["full_sentence_distractors"] + groups["imagined_sentence_distractors"]
    all_targets_ex_incl = all_targets_ex_excl + groups["examples_targets"]
    all_dist_ex_incl    = all_dist_ex_excl + groups["examples_distractors"]

    print_summary_stats("all-targets-examples-excluded",    all_targets_ex_excl, L)
    print_summary_stats("all-distractors-examples-excluded", all_dist_ex_excl, L)
    print_summary_stats("all-targets-examples-included",    all_targets_ex_incl, L)
    print_summary_stats("all-distractors-examples-included", all_dist_ex_incl, L)

    # File-count verification
    L.log("-" * 60)
    L.log("Output folder file counts:")
    for sub in [
        "examples/targets", "examples/distractors",
        "full_sentence/targets", "full_sentence/distractors",
        "imagined_sentence/targets", "imagined_sentence/distractors",
    ]:
        d = out_root / sub
        count = len(list(d.glob("*.wav"))) if d.exists() else 0
        L.log(f"  {sub}: {count} files")
    L.log()

    # Cross-check
    L.log("-" * 60)
    L.log("Cross-check: No stimulus appears in multiple sub-folders")
    all_sets = {}
    for sub in [
        "examples/targets", "examples/distractors",
        "full_sentence/targets", "full_sentence/distractors",
        "imagined_sentence/targets", "imagined_sentence/distractors",
    ]:
        d = out_root / sub
        nums = set()
        for f in d.glob("*.wav"):
            try:
                nums.add(int(f.stem))
            except ValueError:
                pass
        all_sets[sub] = nums

    target_groups = ["examples/targets", "full_sentence/targets", "imagined_sentence/targets"]
    dist_groups   = ["examples/distractors", "full_sentence/distractors", "imagined_sentence/distractors"]

    overlap_found = False
    for i, g1 in enumerate(target_groups):
        for g2 in target_groups[i + 1:]:
            overlap = all_sets[g1] & all_sets[g2]
            if overlap:
                L.log(f"  OVERLAP between {g1} and {g2}: {sorted(overlap)}")
                overlap_found = True
    for i, g1 in enumerate(dist_groups):
        for g2 in dist_groups[i + 1:]:
            overlap = all_sets[g1] & all_sets[g2]
            if overlap:
                L.log(f"  OVERLAP between {g1} and {g2}: {sorted(overlap)}")
                overlap_found = True

    if not overlap_found:
        L.log("  ** CONFIRMED: No overlapping stimuli between any sub-folders **")

    total_targets = sum(len(all_sets[g]) for g in target_groups)
    total_dists   = sum(len(all_sets[g]) for g in dist_groups)
    L.log(f"\n  Total unique targets    : {total_targets}  (expected {TOP_N})")
    L.log(f"  Total unique distractors: {total_dists}  (expected {TOP_N})")

    if total_targets == TOP_N and total_dists == TOP_N:
        L.log("  ** CONFIRMED: All 153 targets and 153 distractors accounted for **")
    else:
        L.log("  ** MISMATCH in totals — investigate **")

    # Optimiser balance report
    L.log()
    L.log("-" * 60)
    L.log("Optimiser Balance Report (full_sentence vs imagined_sentence):")
    for pool_label, g1_key, g2_key in [
        ("Targets",     "full_sentence_targets",     "imagined_sentence_targets"),
        ("Distractors", "full_sentence_distractors", "imagined_sentence_distractors"),
    ]:
        rs1 = [r for _, r in groups[g1_key]]
        rs2 = [r for _, r in groups[g2_key]]
        s1 = stats_tuple(rs1)
        s2 = stats_tuple(rs2)
        c = split_cost(rs1, rs2)
        L.log(f"\n  {pool_label}:")
        L.log(f"    full_sentence      : n={len(rs1):3d}  min={s1[0]:.10f}  max={s1[1]:.10f}  mean={s1[2]:.10f}  median={s1[3]:.10f}")
        L.log(f"    imagined_sentence  : n={len(rs2):3d}  min={s2[0]:.10f}  max={s2[1]:.10f}  mean={s2[2]:.10f}  median={s2[3]:.10f}")
        L.log(f"    Squared-diff cost  : {c:.2e}")

    L.log("\n[STEP 6 COMPLETE]\n")


# ══════════════════════════════════════════════════════════════════════════
# STEP 7 — RMS normalisation  (from normalize_wavs_rms.py)
# ══════════════════════════════════════════════════════════════════════════
def _db_to_linear(db):
    return 10 ** (db / 20.0)


def _linear_to_db(x):
    return 20.0 * np.log10(x)


def _to_mono(x):
    return np.mean(x, axis=1) if x.ndim > 1 else x


def _rms(x, eps=1e-12):
    return float(np.sqrt(np.mean(np.square(x)) + eps))


def _measure_file(path: Path):
    data, sr = sf.read(path, always_2d=False)
    if data.size == 0:
        return {"sr": sr, "peak": 0.0, "rms": 0.0, "status": "empty"}
    peak = float(np.max(np.abs(data)))
    if peak == 0.0:
        return {"sr": sr, "peak": 0.0, "rms": 0.0, "status": "silence"}
    mono = _to_mono(data).astype(np.float64)
    return {"sr": sr, "peak": peak, "rms": _rms(mono), "status": "ok"}


def _normalize_one(in_path: Path, target_rms_dbfs: float, peak_ceiling_dbfs: float,
                    verbose: bool, L):
    data, sr = sf.read(in_path, always_2d=False)
    info = sf.info(in_path)

    if data.size == 0:
        return "empty"
    peak_in = float(np.max(np.abs(data)))
    if peak_in == 0.0:
        return "silence"

    mono = _to_mono(data).astype(np.float64)
    rms_in = _rms(mono)

    target_rms = _db_to_linear(target_rms_dbfs)
    gain = target_rms / rms_in

    peak_ceiling = _db_to_linear(peak_ceiling_dbfs)
    max_gain = peak_ceiling / peak_in
    if gain > max_gain:
        gain = max_gain

    out = data * gain
    rms_out = _rms(_to_mono(out).astype(np.float64))

    # Write in-place
    sf.write(in_path, out, sr, subtype=info.subtype, format=info.format)

    if verbose:
        L.log(f"    {in_path.name}: gain {_linear_to_db(gain):+.2f} dB, "
              f"RMS {_linear_to_db(rms_in):.2f}->{_linear_to_db(rms_out):.2f} dBFS")

    return "ok"


def step7_rms_normalize(out_root: Path, L,
                        target_rms_dbfs=TARGET_RMS_DBFS,
                        peak_ceiling_dbfs=PEAK_CEILING_DBFS,
                        verbose=False):
    L.log("=" * 80)
    L.log("STEP 7: RMS Normalisation")
    L.log("=" * 80)

    # Collect all WAVs under the stimulus sub-folders only
    stim_dirs = [
        "examples/targets", "examples/distractors",
        "full_sentence/targets", "full_sentence/distractors",
        "imagined_sentence/targets", "imagined_sentence/distractors",
    ]

    wavs = []
    for sub in stim_dirs:
        d = out_root / sub
        if d.exists():
            wavs.extend(sorted(d.glob("*.wav")))

    L.log(f"  Stimulus WAV files to normalise: {len(wavs)}")

    if not wavs:
        L.log("  No WAV files found — skipping.")
        L.log("\n[STEP 7 COMPLETE]\n")
        return

    # Pre-scan to compute safe global target
    peak_ceiling = _db_to_linear(peak_ceiling_dbfs)
    achievable = []
    for p in wavs:
        m = _measure_file(p)
        if m["status"] == "ok":
            max_gain = peak_ceiling / m["peak"]
            achievable.append(m["rms"] * max_gain)

    if not achievable:
        L.log("  All files are silent/empty — skipping.")
        L.log("\n[STEP 7 COMPLETE]\n")
        return

    safe_target_rms = min(achievable)
    safe_target_db  = _linear_to_db(safe_target_rms)
    chosen_target   = min(target_rms_dbfs, safe_target_db)

    L.log(f"  Requested target RMS   : {target_rms_dbfs:.2f} dBFS")
    L.log(f"  Max safe target RMS    : {safe_target_db:.2f} dBFS")
    L.log(f"  Using target RMS       : {chosen_target:.2f} dBFS (no clipping)")
    L.log()

    # Normalise in-place
    for p in wavs:
        _normalize_one(p, chosen_target, peak_ceiling_dbfs, verbose, L)

    L.log(f"\n  Normalised {len(wavs)} files in-place.")
    L.log("\n[STEP 7 COMPLETE]\n")


# ══════════════════════════════════════════════════════════════════════════
# STEP 8 — Final gain verification  (from check_audio_gain.py)
# ══════════════════════════════════════════════════════════════════════════
def _get_rms_db(filepath):
    with wave.open(str(filepath), 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth  = wf.getsampwidth()
        sr         = wf.getframerate()
        n_frames   = wf.getnframes()
        raw        = wf.readframes(n_frames)

    if sampwidth == 2:
        dtype = np.int16;  max_val = 32768.0
    elif sampwidth == 1:
        dtype = np.uint8;  max_val = 128.0
    elif sampwidth == 4:
        dtype = np.int32;  max_val = 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    samples = np.frombuffer(raw, dtype=dtype).astype(np.float64)
    if n_channels == 2:
        samples = samples.reshape(-1, 2).mean(axis=1)
    samples /= max_val

    rms_val = np.sqrt(np.mean(samples ** 2))
    rms_db  = 20 * np.log10(rms_val) if rms_val > 0 else -np.inf
    peak    = np.max(np.abs(samples))
    peak_db = 20 * np.log10(peak) if peak > 0 else -np.inf
    return rms_db, peak_db, sr


def step8_verify_gain(out_root: Path, L):
    L.log("=" * 80)
    L.log("STEP 8: Final Gain Verification (check_audio_gain)")
    L.log("=" * 80)
    L.log()

    wav_files = sorted(out_root.rglob("*.wav"))
    L.log(f"  Found {len(wav_files)} WAV files in {out_root.name}/")
    L.log()

    header = f"  {'File':<55} {'RMS(dB)':>9} {'Peak(dB)':>9} {'SR':>6}"
    L.log(header)
    L.log("  " + "-" * 82)

    results = []
    rms_stim = []

    for wav in wav_files:
        try:
            rms_db, peak_db, sr = _get_rms_db(wav)
            rel = str(wav.relative_to(out_root))
            results.append((rel, rms_db, peak_db, sr))
            parts = wav.relative_to(out_root).parts
            if len(parts) >= 3:
                rms_stim.append((rel, rms_db))
        except Exception as e:
            rel = str(wav.relative_to(out_root))
            L.log(f"  {rel:<55} ERROR: {e}")

    for rel, rms_db, peak_db, sr in results:
        rms_s  = f"{rms_db:.2f}" if rms_db != -np.inf else "-inf"
        peak_s = f"{peak_db:.2f}" if peak_db != -np.inf else "-inf"
        L.log(f"  {rel:<55} {rms_s:>9} {peak_s:>9} {sr:>6}")

    L.log()

    if rms_stim:
        vals = [v for _, v in rms_stim if v != -np.inf]
        mn, mx = min(vals), max(vals)
        mu = np.mean(vals)
        sd = np.std(vals)
        spread = mx - mn

        L.log("  Stimulus files RMS summary:")
        L.log(f"    Count      : {len(vals)}")
        L.log(f"    Min RMS    : {mn:.2f} dB")
        L.log(f"    Max RMS    : {mx:.2f} dB")
        L.log(f"    Mean RMS   : {mu:.2f} dB")
        L.log(f"    Std Dev    : {sd:.4f} dB")
        L.log(f"    Spread     : {spread:.4f} dB")
        L.log()

        tolerance = 1.0
        if spread < 0.01:
            L.log("    ** CONFIRMED: All stimulus files have identical RMS levels **")
        elif spread <= tolerance:
            L.log(f"    ** All stimulus files are within {spread:.2f} dB — CONSISTENT **")
        else:
            L.log(f"    ** WARNING: Spread > {tolerance} dB ({spread:.2f} dB) — INCONSISTENT **")
            outliers = [(r, v) for r, v in rms_stim if v != -np.inf and abs(v - mu) > 0.5]
            if outliers:
                L.log("    Outliers (>0.5 dB from mean):")
                for r, v in outliers[:20]:
                    L.log(f"      {r}: {v:.2f} dB ({v - mu:+.2f})")

    L.log("\n[STEP 8 COMPLETE]\n")


# ══════════════════════════════════════════════════════════════════════════
# SINGLE-FOLDER PIPELINE  (steps 1–8)
# ══════════════════════════════════════════════════════════════════════════
def run_pipeline_for_folder(copy_folder: Path, out_root: Path,
                            wall_wav: Path, dry_run=False, verbose=False):
    """Run the complete pipeline for one copy_folder → audio_stimuli pair."""
    L = PipelineLogger()

    L.log("=" * 80)
    L.log(f"  STIMULI PREPARATION PIPELINE  —  {copy_folder.name} → {out_root.name}")
    L.log(f"  Started: {datetime.now().isoformat()}")
    L.log("=" * 80)
    L.log()

    # Resolve paths inside copy_folder
    pearson_csv    = copy_folder / "correlation_csvs" / "pearson_scores.csv"
    corr_csv_dir   = copy_folder / "correlation_csvs"
    targets_dir    = copy_folder / "targets"
    distractors_dir = copy_folder / "distractors"

    # Discover numbered reference files
    folder_number = None
    m = re.match(r"wall_(\d+)", next((f.stem for f in copy_folder.glob("wall_*.wav")), ""))
    if m:
        folder_number = m.group(1)
    else:
        # fallback: try to get from parent folder name
        folder_number = copy_folder.parent.name if copy_folder.parent.name.isdigit() else None

    wall_wav = copy_folder / f"wall_{folder_number}.wav" if folder_number else None
    fullsentence_wav = copy_folder / f"fullsentence_{folder_number}.wav" if folder_number else None
    fullsentenceminuswall_wav = copy_folder / f"fullsentenceminuswall_{folder_number}.wav" if folder_number else None

    # Validate prerequisites
    for p, desc in [
        (copy_folder,      "copy folder"),
        (pearson_csv,      "pearson_scores.csv"),
        (targets_dir,      "targets/"),
        (distractors_dir,  "distractors/"),
        (wall_wav,         f"wall_{folder_number}.wav reference"),
        (fullsentence_wav, f"fullsentence_{folder_number}.wav reference"),
        (fullsentenceminuswall_wav, f"fullsentenceminuswall_{folder_number}.wav reference"),
    ]:
        if not p or not p.exists():
            L.log(f"  ERROR: {desc} not found at {p}")
            L.log("  ABORTING this folder.")
            log_file = out_root / "pipeline_output_log.txt"
            out_root.mkdir(parents=True, exist_ok=True)
            L.flush_to(log_file)
            return False

    if dry_run:
        L.log("  [DRY RUN] — would process this folder. Skipping.\n")
        return True

    # Clean/create output
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)

    # Step 1
    high_153, low_153 = step1_create_correlation_csvs(pearson_csv, corr_csv_dir, L)
    # Optionally: add comparison logic for wall_{number}.wav, fullsentence_{number}.wav, fullsentenceminuswall_{number}.wav here
    # For example, validate their properties or log their stats
    for ref_file, ref_name in [
        (wall_wav, f"wall_{folder_number}.wav"),
        (fullsentence_wav, f"fullsentence_{folder_number}.wav"),
        (fullsentenceminuswall_wav, f"fullsentenceminuswall_{folder_number}.wav")
    ]:
        if ref_file and ref_file.exists():
            info = sf.info(str(ref_file))
            L.log(f"Reference {ref_name}: SR={info.samplerate}, Channels={info.channels}, Frames={info.frames}, Subtype={info.subtype}")
        else:
            L.log(f"Reference {ref_name} missing or not found.")

    # Step 2
    targets_ok = step2_verify_targets(high_153, targets_dir, L)

    # Step 3
    distractors_ok = step3_verify_distractors(low_153, distractors_dir, L)

    if not targets_ok or not distractors_ok:
        L.log("*** ABORTING: File verification failed. See above. ***")
        L.flush_to(out_root / "pipeline_output_log.txt")
        return False

    # Step 4
    audio_ok = step4_validate_audio(targets_dir, distractors_dir, wall_wav, L)
    if not audio_ok:
        L.log("*** WARNING: Audio validation issues found. Proceeding anyway. ***")

    # Step 5
    groups = step5_split_and_copy(
        high_153, low_153,
        targets_dir, distractors_dir,
        corr_csv_dir, out_root, L
    )
    if groups is None:
        L.log("*** ABORTING: Split failed. ***")
        L.flush_to(out_root / "pipeline_output_log.txt")
        return False

    # Step 6
    step6_statistics(groups, out_root, L)

    # Step 7 — RMS normalise
    step7_rms_normalize(out_root, L, verbose=verbose)

    # Step 8 — Final gain verification
    step8_verify_gain(out_root, L)

    # Done
    L.log("=" * 80)
    L.log("  PIPELINE COMPLETE")
    L.log(f"  Finished: {datetime.now().isoformat()}")
    L.log(f"  Output: {out_root}")
    L.log("=" * 80)

    L.flush_to(out_root / "pipeline_output_log.txt")
    return True


# ══════════════════════════════════════════════════════════════════════════
# DISCOVERY + BATCH RUNNER
# ══════════════════════════════════════════════════════════════════════════
def discover_copy_folders(root: Path):
    """Find all potential_stimuli/*/copy_folder directories and return sorted (number, path) list."""
    results = []
    for subdir in (root / "potential_stimuli").iterdir():
        if not subdir.is_dir():
            continue
        try:
            n = int(subdir.name)
        except ValueError:
            continue
        copy_folder = subdir / "copy_folder"
        if copy_folder.is_dir():
            results.append((n, copy_folder))
    return sorted(results, key=lambda x: x[0])


def main():
    ap = argparse.ArgumentParser(
        description="Batch stimuli preparation pipeline. "
                    "Processes copy_folder_{N} → audio_stimuli_{N}."
    )
    ap.add_argument(
        "numbers", nargs="*", type=int,
        help="Specific folder numbers to process (default: auto-discover all)"
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Preview which folders would be processed without writing anything"
    )
    ap.add_argument(
        "--verbose", action="store_true",
        help="Print per-file RMS normalisation details"
    )
    ap.add_argument(
        "--wall-wav", type=str, default=None,
        help=f"Path to reference wall.wav (default: {WALL_WAV})"
    )
    args = ap.parse_args()

    wall_wav = Path(args.wall_wav).resolve() if args.wall_wav else WALL_WAV

    if not wall_wav.exists():
        print(f"ERROR: Reference wall.wav not found at {wall_wav}")
        print("       Use --wall-wav to specify the correct path.")
        sys.exit(1)

    # Determine which folders to process
    if args.numbers:
        folders = []
        for n in args.numbers:
            d = PROJECT_ROOT / "potential_stimuli" / str(n) / "copy_folder"
            if not d.exists():
                print(f"WARNING: potential_stimuli/{n}/copy_folder does not exist — skipping")
                continue
            folders.append((n, d))
    else:
        folders = discover_copy_folders(PROJECT_ROOT)

    if not folders:
        print("No copy_folder_{N} directories found. Nothing to do.")
        sys.exit(0)

    print("=" * 80)
    print("  BATCH STIMULI PIPELINE")
    print(f"  {datetime.now().isoformat()}")
    print(f"  Reference wall.wav: {wall_wav}")
    print(f"  Folders to process: {len(folders)}")
    for n, d in folders:
        print(f"    copy_folder_{n} → audio_stimuli_{n}")
    print("=" * 80)
    print()

    results = {}
    for n, copy_dir in folders:
        out_dir = PROJECT_ROOT / f"audio_stimuli_{n}"
        print(f"\n{'━' * 80}")
        print(f"  Processing copy_folder_{n} → audio_stimuli_{n}")
        print(f"{'━' * 80}\n")

        ok = run_pipeline_for_folder(
            copy_folder=copy_dir,
            out_root=out_dir,
            wall_wav=wall_wav,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        results[n] = "PASS" if ok else "FAIL"

    # Final summary
    print("\n" + "=" * 80)
    print("  BATCH SUMMARY")
    print("=" * 80)
    for n in sorted(results):
        status = results[n]
        marker = "✓" if status == "PASS" else "✗"
        print(f"    {marker}  copy_folder_{n} → audio_stimuli_{n} : {status}")
    print("=" * 80)

    if any(v == "FAIL" for v in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
