#!/usr/bin/env python3
"""
==========================================================================
  Stimuli Preparation Pipeline
==========================================================================
  Processes copy_folder/ into the final audio_stimuli/ directory structure.

  Steps:
    1. Read pearson_scores.csv and create high/low correlation CSVs
    2. Verify copy_folder/targets match top 153 by raw pearson score
    3. Verify copy_folder/distractors match bottom 153 by |pearson score|
    4. Validate audio properties (mono, 8kHz, 16-bit PCM, frame count)
    5. Split into full_sentence/imagined_sentence/examples sub-folders
    6. Compute and report summary statistics for every condition

  All console output is mirrored to   pipeline_output_log.txt
==========================================================================
"""

import csv
import math
import os
import random
import shutil
import sys
import wave
from datetime import datetime
from io import StringIO
from pathlib import Path
from statistics import median

import numpy as np
import soundfile as sf

# ──────────────────────────────────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
COPY_FOLDER = SCRIPT_DIR / "copy_folder"
PEARSON_CSV = COPY_FOLDER / "correlation_csvs" / "pearson_scores.csv"
CORR_CSV_DIR = COPY_FOLDER / "correlation_csvs"
TARGETS_DIR = COPY_FOLDER / "targets"
DISTRACTORS_DIR = COPY_FOLDER / "distractors"
WALL_WAV = SCRIPT_DIR / "audio_stimuli_old" / "wall.wav"

OUT_ROOT = SCRIPT_DIR / "audio_stimuli"
LOG_FILE = SCRIPT_DIR / "pipeline_output_log.txt"

# ──────────────────────────────────────────────────────────────────────────
# SPLIT PARAMETERS  (must sum to 153 per pool)
# ──────────────────────────────────────────────────────────────────────────
EXAMPLES_PER_POOL = 3            # examples/targets and examples/distractors
MAIN_PER_SUBFOLDER = 75          # full_sentence + imagined_sentence each
TOP_N = 153                      # total targets / distractors
assert EXAMPLES_PER_POOL + 2 * MAIN_PER_SUBFOLDER == TOP_N

# Optimiser knobs (same as split_new_h_wavs.py)
INIT_METHOD = "snake"
ITERATIONS = 200_000
SEED_HIGH = 42
SEED_LOW = 43

# ──────────────────────────────────────────────────────────────────────────
# LOGGING HELPER  –  tee every print to both console and log file
# ──────────────────────────────────────────────────────────────────────────
_log_buffer = StringIO()


def log(msg=""):
    """Print to stdout AND accumulate into log buffer."""
    print(msg)
    _log_buffer.write(msg + "\n")


def flush_log():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(_log_buffer.getvalue())
    print(f"\n[LOG SAVED] {LOG_FILE}")


# ──────────────────────────────────────────────────────────────────────────
# STEP 1  —  Create high_correlation_stimuli.csv & low_correlation_stimuli.csv
# ──────────────────────────────────────────────────────────────────────────
def step1_create_correlation_csvs():
    log("=" * 80)
    log("STEP 1: Create high_correlation_stimuli.csv and low_correlation_stimuli.csv")
    log("=" * 80)
    log(f"Source CSV : {PEARSON_CSV}")
    log(f"Output dir : {CORR_CSV_DIR}")
    log()

    # Read the full CSV
    rows = []
    with open(PEARSON_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    log(f"Total rows in pearson_scores.csv: {len(rows)}")

    # Parse into (chunk_number, r_score) tuples
    parsed = []
    for row in rows:
        try:
            chunk_num = int(row["chunk_number"])
            r_score = float(row["r_score"])
            parsed.append((chunk_num, r_score))
        except (ValueError, KeyError):
            continue
    log(f"Successfully parsed rows: {len(parsed)}")

    # ── HIGH: top 153 by raw r_score (descending) ──
    sorted_by_raw = sorted(parsed, key=lambda x: x[1], reverse=True)
    high_153 = sorted_by_raw[:TOP_N]

    high_csv_path = CORR_CSV_DIR / "high_correlation_stimuli.csv"
    with open(high_csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stimulus_number", "r_score"])
        for chunk_num, r in high_153:
            w.writerow([chunk_num, r])
    log(f"\nWrote {high_csv_path.name}  ({len(high_153)} rows)")
    log(f"  Highest r_score : {high_153[0][1]}")
    log(f"  Lowest  r_score : {high_153[-1][1]}")
    log(f"  Chunk #s (first 10): {[h[0] for h in high_153[:10]]}")

    # ── LOW: bottom 153 by abs(r_score) (ascending) ──
    sorted_by_abs = sorted(parsed, key=lambda x: abs(x[1]))
    low_153 = sorted_by_abs[:TOP_N]

    low_csv_path = CORR_CSV_DIR / "low_correlation_stimuli.csv"
    with open(low_csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stimulus_number", "r_score"])
        for chunk_num, r in low_153:
            w.writerow([chunk_num, r])
    log(f"\nWrote {low_csv_path.name}  ({len(low_153)} rows)")
    log(f"  Smallest |r_score| : {abs(low_153[0][1])}")
    log(f"  Largest  |r_score| : {abs(low_153[-1][1])}")
    log(f"  Chunk #s (first 10): {[l[0] for l in low_153[:10]]}")

    log("\n[STEP 1 COMPLETE]\n")
    return high_153, low_153


# ──────────────────────────────────────────────────────────────────────────
# STEP 2  —  Verify targets folder matches high correlation CSV
# ──────────────────────────────────────────────────────────────────────────
def step2_verify_targets(high_153):
    log("=" * 80)
    log("STEP 2: Verify copy_folder/targets contains exactly the top 153 stimuli")
    log("=" * 80)

    expected_nums = {h[0] for h in high_153}
    actual_files = list(TARGETS_DIR.glob("*.wav"))
    actual_nums = set()
    for f in actual_files:
        # filenames are chunk_XXXXXX.wav
        try:
            num = int(f.stem.split("_")[1])
            actual_nums.add(num)
        except (IndexError, ValueError):
            log(f"  WARNING: Could not parse filename: {f.name}")

    log(f"Expected target count : {len(expected_nums)}")
    log(f"Actual   target count : {len(actual_nums)}")

    missing = expected_nums - actual_nums
    extra = actual_nums - expected_nums

    if missing:
        log(f"\n  MISSING from targets/ ({len(missing)}): {sorted(missing)}")
    if extra:
        log(f"\n  EXTRA in targets/ ({len(extra)}): {sorted(extra)}")

    if not missing and not extra and len(actual_nums) == TOP_N:
        log("\n  ** CONFIRMED: targets/ contains exactly the top 153 high-correlation stimuli **")
        match = True
    else:
        log("\n  ** MISMATCH DETECTED — see details above **")
        match = False

    log("\n[STEP 2 COMPLETE]\n")
    return match


# ──────────────────────────────────────────────────────────────────────────
# STEP 3  —  Verify distractors folder matches low correlation CSV
# ──────────────────────────────────────────────────────────────────────────
def step3_verify_distractors(low_153):
    log("=" * 80)
    log("STEP 3: Verify copy_folder/distractors contains exactly the bottom 153 stimuli")
    log("=" * 80)

    expected_nums = {l[0] for l in low_153}
    actual_files = list(DISTRACTORS_DIR.glob("*.wav"))
    actual_nums = set()
    for f in actual_files:
        try:
            num = int(f.stem.split("_")[1])
            actual_nums.add(num)
        except (IndexError, ValueError):
            log(f"  WARNING: Could not parse filename: {f.name}")

    log(f"Expected distractor count : {len(expected_nums)}")
    log(f"Actual   distractor count : {len(actual_nums)}")

    missing = expected_nums - actual_nums
    extra = actual_nums - expected_nums

    if missing:
        log(f"\n  MISSING from distractors/ ({len(missing)}): {sorted(missing)}")
    if extra:
        log(f"\n  EXTRA in distractors/ ({len(extra)}): {sorted(extra)}")

    if not missing and not extra and len(actual_nums) == TOP_N:
        log("\n  ** CONFIRMED: distractors/ contains exactly the bottom 153 low-correlation stimuli **")
        match = True
    else:
        log("\n  ** MISMATCH DETECTED — see details above **")
        match = False

    log("\n[STEP 3 COMPLETE]\n")
    return match


# ──────────────────────────────────────────────────────────────────────────
# STEP 4  —  Validate audio properties of every WAV
# ──────────────────────────────────────────────────────────────────────────
def step4_validate_audio():
    log("=" * 80)
    log("STEP 4: Validate audio properties (mono, 8 kHz, PCM_16, frame count)")
    log("=" * 80)

    # Reference: wall.wav
    wall_info = sf.info(str(WALL_WAV))
    ref_frames = wall_info.frames
    ref_sr = int(wall_info.samplerate)
    ref_channels = wall_info.channels
    ref_subtype = wall_info.subtype

    log(f"\nReference file: {WALL_WAV.name}")
    log(f"  Sample rate : {ref_sr} Hz")
    log(f"  Channels    : {ref_channels}")
    log(f"  Frames      : {ref_frames}")
    log(f"  Subtype     : {ref_subtype}")
    log(f"  Duration    : {ref_frames / ref_sr:.4f} s")
    log()

    all_ok = True
    issues = []

    for label, folder in [("targets", TARGETS_DIR), ("distractors", DISTRACTORS_DIR)]:
        wavs = sorted(folder.glob("*.wav"))
        log(f"Checking {label}/ — {len(wavs)} files")
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
                log(msg)
                issues.append(msg)
                folder_ok = False
                all_ok = False

        if folder_ok:
            log(f"  All {len(wavs)} files in {label}/ PASSED")
            log(f"    Channels   : 1 (mono)")
            log(f"    Sample rate: 8000 Hz")
            log(f"    Subtype    : PCM_16 (16-bit)")
            log(f"    Frames     : {ref_frames} (matches wall.wav)")
        log()

    if all_ok:
        log("  ** CONFIRMED: All 306 stimuli files are mono, 8 kHz, 16-bit PCM, "
            f"and have {ref_frames} frames (matching wall.wav) **")
    else:
        log(f"  ** {len(issues)} ISSUE(S) FOUND — see details above **")

    log("\n[STEP 4 COMPLETE]\n")
    return all_ok


# ──────────────────────────────────────────────────────────────────────────
# STEP 5  —  Split into final folder structure
# ──────────────────────────────────────────────────────────────────────────

def stats_tuple(rs):
    """Return (min, max, mean, median) for a list of r_scores."""
    mu = sum(rs) / len(rs)
    return (min(rs), max(rs), float(mu), float(median(rs)))


def cost(rs_a, rs_b):
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

    # Snake for 2 groups
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
    current_cost = cost([rs[i] for i in A], [rs[i] for i in B])
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

        new_cost = cost([rs[k] for k in A2], [rs[k] for k in B2])
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


def step5_split_and_copy(high_153, low_153):
    log("=" * 80)
    log("STEP 5: Split 153 targets + 153 distractors into final folder structure")
    log("=" * 80)
    log(f"  Output root       : {OUT_ROOT}")
    log(f"  Examples per pool  : {EXAMPLES_PER_POOL}")
    log(f"  Main per subfolder : {MAIN_PER_SUBFOLDER}")
    log(f"  Optimiser iters    : {ITERATIONS}")
    log(f"  Init method        : {INIT_METHOD}")
    log()

    # Build output directories
    for sub in [
        "examples/targets", "examples/distractors",
        "full_sentence/targets", "full_sentence/distractors",
        "imagined_sentence/targets", "imagined_sentence/distractors",
        "correlation_csvs",
    ]:
        (OUT_ROOT / sub).mkdir(parents=True, exist_ok=True)

    # ── Select examples ──
    # Sort high by r_score descending; pick examples that span the range
    # We use a deterministic seed for reproducibility
    rng = random.Random(99)

    high_nums = [h[0] for h in high_153]
    low_nums = [l[0] for l in low_153]

    high_example_nums = set(rng.sample(high_nums, EXAMPLES_PER_POOL))
    low_example_nums = set(rng.sample(low_nums, EXAMPLES_PER_POOL))

    log(f"Selected example targets     : {sorted(high_example_nums)}")
    log(f"Selected example distractors : {sorted(low_example_nums)}")

    # Map chunk_number -> r_score for quick lookup
    high_dict = {h[0]: h[1] for h in high_153}
    low_dict = {l[0]: l[1] for l in low_153}

    # Copy examples
    for num in sorted(high_example_nums):
        src = TARGETS_DIR / f"chunk_{num}.wav"
        dst = OUT_ROOT / "examples" / "targets" / f"{num}.wav"
        shutil.copy2(src, dst)
        log(f"  Copied example target: chunk_{num}.wav -> examples/targets/{num}.wav  (r={high_dict[num]:.10f})")

    for num in sorted(low_example_nums):
        src = DISTRACTORS_DIR / f"chunk_{num}.wav"
        dst = OUT_ROOT / "examples" / "distractors" / f"{num}.wav"
        shutil.copy2(src, dst)
        log(f"  Copied example distractor: chunk_{num}.wav -> examples/distractors/{num}.wav  (r={low_dict[num]:.15e})")

    # ── Remaining items for optimised split ──
    high_remaining = [(n, r) for n, r in high_153 if n not in high_example_nums]
    low_remaining = [(n, r) for n, r in low_153 if n not in low_example_nums]

    log(f"\nHigh remaining for split: {len(high_remaining)}  (expected {MAIN_PER_SUBFOLDER * 2})")
    log(f"Low  remaining for split: {len(low_remaining)}  (expected {MAIN_PER_SUBFOLDER * 2})")

    if len(high_remaining) != MAIN_PER_SUBFOLDER * 2:
        log(f"  ERROR: Expected {MAIN_PER_SUBFOLDER * 2} high items, got {len(high_remaining)}")
        return None
    if len(low_remaining) != MAIN_PER_SUBFOLDER * 2:
        log(f"  ERROR: Expected {MAIN_PER_SUBFOLDER * 2} low items, got {len(low_remaining)}")
        return None

    # ── Optimise split for high (targets) ──
    log(f"\nOptimising high-correlation split (full_sentence vs imagined_sentence targets)...")
    log(f"  Iterations: {ITERATIONS}, Seed: {SEED_HIGH}, Init: {INIT_METHOD}")
    high_A, high_B = optimize_two_groups(
        high_remaining, target_size=MAIN_PER_SUBFOLDER,
        iterations=ITERATIONS, seed=SEED_HIGH, init_method=INIT_METHOD
    )
    log("  Done.")

    # ── Optimise split for low (distractors) ──
    log(f"\nOptimising low-correlation split (full_sentence vs imagined_sentence distractors)...")
    log(f"  Iterations: {ITERATIONS}, Seed: {SEED_LOW}, Init: {INIT_METHOD}")
    low_A, low_B = optimize_two_groups(
        low_remaining, target_size=MAIN_PER_SUBFOLDER,
        iterations=ITERATIONS, seed=SEED_LOW, init_method=INIT_METHOD
    )
    log("  Done.")

    # ── Copy files ──
    copy_map = [
        ("full_sentence/targets",           TARGETS_DIR,     high_A),
        ("imagined_sentence/targets",       TARGETS_DIR,     high_B),
        ("full_sentence/distractors",       DISTRACTORS_DIR, low_A),
        ("imagined_sentence/distractors",   DISTRACTORS_DIR, low_B),
    ]

    for subfolder, src_dir, group in copy_map:
        dest_dir = OUT_ROOT / subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)
        log(f"\nCopying {len(group)} files -> {subfolder}/")
        for stim_num, r_score in group:
            src = src_dir / f"chunk_{stim_num}.wav"
            dst = dest_dir / f"{stim_num}.wav"
            shutil.copy2(src, dst)
        log(f"  Copied {len(group)} files to {subfolder}/")

    # ── Copy correlation CSVs into output ──
    for csv_name in ["high_correlation_stimuli.csv", "low_correlation_stimuli.csv"]:
        src = CORR_CSV_DIR / csv_name
        dst = OUT_ROOT / "correlation_csvs" / csv_name
        shutil.copy2(src, dst)
        log(f"\nCopied {csv_name} -> audio_stimuli/correlation_csvs/")

    log("\n[STEP 5 COMPLETE]\n")

    # Return the groups for statistics
    return {
        "full_sentence_targets": high_A,
        "imagined_sentence_targets": high_B,
        "full_sentence_distractors": low_A,
        "imagined_sentence_distractors": low_B,
        "examples_targets": [(n, high_dict[n]) for n in sorted(high_example_nums)],
        "examples_distractors": [(n, low_dict[n]) for n in sorted(low_example_nums)],
    }


# ──────────────────────────────────────────────────────────────────────────
# STEP 6  —  Summary statistics
# ──────────────────────────────────────────────────────────────────────────
def print_summary_stats(label, group):
    """Print verbose summary stats for a list of (stim_num, r_score) tuples."""
    rs = [r for _, r in group]
    n = len(rs)
    if n == 0:
        log(f"Summary Statistics for {label} (n = 0) — EMPTY")
        return

    mu = np.mean(rs)
    sd = np.std(rs)
    mn = np.min(rs)
    mx = np.max(rs)
    rng = mx - mn
    med = float(np.median(rs))

    log(f"Summary Statistics for {label} condition (n = {n})")
    log("=" * 60)
    log(f"  Mean   : {mu}")
    log(f"  Std    : {sd}")
    log(f"  Range  : {rng}")
    log(f"  Max    : {mx}")
    log(f"  Min    : {mn}")
    log(f"  Median : {med}")

    # List all stimuli in this group
    log(f"  Stimuli: {sorted([s for s, _ in group])}")
    log()


def step6_statistics(groups):
    log("=" * 80)
    log("STEP 6: Summary Statistics for All Conditions")
    log("=" * 80)
    log()

    # Individual conditions
    condition_labels = [
        ("full_sentence-targets",           "full_sentence_targets"),
        ("full_sentence-distractors",       "full_sentence_distractors"),
        ("imagined_sentence-targets",       "imagined_sentence_targets"),
        ("imagined_sentence-distractors",   "imagined_sentence_distractors"),
        ("examples-targets",                "examples_targets"),
        ("examples-distractors",            "examples_distractors"),
    ]

    for label, key in condition_labels:
        print_summary_stats(label, groups[key])

    # Super-lists
    all_targets_ex_excl = groups["full_sentence_targets"] + groups["imagined_sentence_targets"]
    all_dist_ex_excl = groups["full_sentence_distractors"] + groups["imagined_sentence_distractors"]
    all_targets_ex_incl = all_targets_ex_excl + groups["examples_targets"]
    all_dist_ex_incl = all_dist_ex_excl + groups["examples_distractors"]

    print_summary_stats("all-targets-examples-excluded", all_targets_ex_excl)
    print_summary_stats("all-distractors-examples-excluded", all_dist_ex_excl)
    print_summary_stats("all-targets-examples-included", all_targets_ex_incl)
    print_summary_stats("all-distractors-examples-included", all_dist_ex_incl)

    # ── Per-subfolder file verification ──
    log("-" * 60)
    log("Output folder file counts:")
    for sub in [
        "examples/targets", "examples/distractors",
        "full_sentence/targets", "full_sentence/distractors",
        "imagined_sentence/targets", "imagined_sentence/distractors",
    ]:
        d = OUT_ROOT / sub
        count = len(list(d.glob("*.wav"))) if d.exists() else 0
        log(f"  {sub}: {count} files")

    log()

    # ── Cross-check: no stimulus appears in more than one subfolder ──
    log("-" * 60)
    log("Cross-check: No stimulus appears in multiple sub-folders")
    all_sets = {}
    for sub in [
        "examples/targets", "examples/distractors",
        "full_sentence/targets", "full_sentence/distractors",
        "imagined_sentence/targets", "imagined_sentence/distractors",
    ]:
        d = OUT_ROOT / sub
        nums = set()
        for f in d.glob("*.wav"):
            try:
                nums.add(int(f.stem))
            except ValueError:
                pass
        all_sets[sub] = nums

    # Check target overlaps
    target_groups = ["examples/targets", "full_sentence/targets", "imagined_sentence/targets"]
    dist_groups = ["examples/distractors", "full_sentence/distractors", "imagined_sentence/distractors"]

    overlap_found = False
    for i, g1 in enumerate(target_groups):
        for g2 in target_groups[i + 1:]:
            overlap = all_sets[g1] & all_sets[g2]
            if overlap:
                log(f"  OVERLAP between {g1} and {g2}: {sorted(overlap)}")
                overlap_found = True

    for i, g1 in enumerate(dist_groups):
        for g2 in dist_groups[i + 1:]:
            overlap = all_sets[g1] & all_sets[g2]
            if overlap:
                log(f"  OVERLAP between {g1} and {g2}: {sorted(overlap)}")
                overlap_found = True

    if not overlap_found:
        log("  ** CONFIRMED: No overlapping stimuli between any sub-folders **")

    # ── Verify totals ──
    total_targets = sum(len(all_sets[g]) for g in target_groups)
    total_dists = sum(len(all_sets[g]) for g in dist_groups)
    log(f"\n  Total unique targets    : {total_targets}  (expected {TOP_N})")
    log(f"  Total unique distractors: {total_dists}  (expected {TOP_N})")

    if total_targets == TOP_N and total_dists == TOP_N:
        log("  ** CONFIRMED: All 153 targets and 153 distractors accounted for **")
    else:
        log("  ** MISMATCH in totals — investigate **")

    # ── Optimiser balance report ──
    log()
    log("-" * 60)
    log("Optimiser Balance Report (full_sentence vs imagined_sentence):")
    for pool_label, g1_key, g2_key in [
        ("Targets", "full_sentence_targets", "imagined_sentence_targets"),
        ("Distractors", "full_sentence_distractors", "imagined_sentence_distractors"),
    ]:
        rs1 = [r for _, r in groups[g1_key]]
        rs2 = [r for _, r in groups[g2_key]]
        s1 = stats_tuple(rs1)
        s2 = stats_tuple(rs2)
        c = cost(rs1, rs2)
        log(f"\n  {pool_label}:")
        log(f"    full_sentence      : n={len(rs1):3d}  min={s1[0]:.10f}  max={s1[1]:.10f}  mean={s1[2]:.10f}  median={s1[3]:.10f}")
        log(f"    imagined_sentence  : n={len(rs2):3d}  min={s2[0]:.10f}  max={s2[1]:.10f}  mean={s2[2]:.10f}  median={s2[3]:.10f}")
        log(f"    Squared-diff cost  : {c:.2e}")

    log("\n[STEP 6 COMPLETE]\n")


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────
def main():
    log("=" * 80)
    log("  STIMULI PREPARATION PIPELINE")
    log(f"  Started: {datetime.now().isoformat()}")
    log("=" * 80)
    log()

    # Step 1
    high_153, low_153 = step1_create_correlation_csvs()

    # Step 2
    targets_ok = step2_verify_targets(high_153)

    # Step 3
    distractors_ok = step3_verify_distractors(low_153)

    if not targets_ok or not distractors_ok:
        log("*** ABORTING: File verification failed. See above. ***")
        flush_log()
        sys.exit(1)

    # Step 4
    audio_ok = step4_validate_audio()
    if not audio_ok:
        log("*** WARNING: Audio validation issues found. Proceeding anyway. ***")

    # Step 5
    groups = step5_split_and_copy(high_153, low_153)
    if groups is None:
        log("*** ABORTING: Split failed. ***")
        flush_log()
        sys.exit(1)

    # Step 6
    step6_statistics(groups)

    # Final summary
    log("=" * 80)
    log("  PIPELINE COMPLETE")
    log(f"  Finished: {datetime.now().isoformat()}")
    log(f"  Output: {OUT_ROOT}")
    log("=" * 80)

    flush_log()


if __name__ == "__main__":
    main()
