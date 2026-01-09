#!/usr/bin/env python3
"""Split `new_h_wavs` WAVs into the 4-folder `new_audio_stimuli` structure.

Uses `new_h_wavs/high.csv` + `new_h_wavs/low.csv` (columns: `stimulus_number`, `r_score`)
to build *exact* 75/75 splits for high and low pools.

Mapping:
- high -> full_sentence/targets (75) + imagined_sentence/targets (75)
- low  -> full_sentence/distractors (75) + imagined_sentence/distractors (75)

The algorithm:
1) Filter CSV rows to files present on disk.
2) Select 150 items per pool (evenly across sorted r_score if more than 150 exist).
3) Initialize a 75/75 partition using a "snake" assignment (balances extremes).
4) Improve via swap-based local search to minimize squared diffs of
   (min, max, mean, median) between the two groups.
5) Copy WAVs and write mapping CSVs.
"""

import csv
import math
import shutil
import random
import os
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent
ROOT_DIR = os.path.dirname(__file__)
SRC = ROOT / 'new_h_wavs'
HIGH_DIR = SRC / 'high_correlation'
LOW_DIR = SRC / 'low_correlation'
HIGH_CSV = SRC / 'high.csv'
LOW_CSV = SRC / 'low.csv'

# Write into the folder your experiment loads from (`helperFunctions.getStimuli()`).
OUT_ROOT = ROOT / 'audio_stimuli'
MAP = {
    0: ('full_sentence', 'targets'),
    1: ('imagined_sentence', 'targets'),
    2: ('full_sentence', 'distractors'),
    3: ('imagined_sentence', 'distractors'),
}

SAMPLES_PER_CORR_PER_SUBFOLDER = 75  # from each of high and low per subfolder
GROUPS = 4
SELECT_PER_POOL = SAMPLES_PER_CORR_PER_SUBFOLDER * GROUPS  # 300

TARGET_SIZE = 75
SELECT_PER_POOL_OPT = TARGET_SIZE * 2  # 150

# Default optimization behavior (no CLI args)
INIT_METHOD = 'snake'      # 'snake' or 'random'
ITERATIONS = 200000        # swap iterations per pool (raise for better matching)
SEED_HIGH = 42
SEED_LOW = 43


def load_csv(csv_path):
    expected = {'stimulus_number', 'r_score'}
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV {csv_path} missing header")
        if not expected.issubset(set(reader.fieldnames)):
            raise ValueError(f"CSV {csv_path} missing columns. Need {expected}")
        rows = []
        for row in reader:
            rows.append(row)
    return rows


def make_output_dirs():
    for g in MAP.values():
        d = OUT_ROOT / g[0] / g[1]
        d.mkdir(parents=True, exist_ok=True)


def get_available_files(pool_dir):
    # return set of stimulus_number ints corresponding to files in dir
    nums = set()
    for p in pool_dir.glob('chunk_*.wav'):
        name = p.stem  # chunk_12345
        try:
            n = int(name.split('_')[1])
            nums.add(n)
        except Exception:
            continue
    return nums


def select_evenly_by_r(rows, available_nums, n):
    items = []
    for row in rows:
        try:
            stim = int(row['stimulus_number'])
            r = float(row['r_score'])
        except Exception:
            continue
        if stim in available_nums:
            items.append((stim, r))

    items.sort(key=lambda x: x[1])
    total = len(items)
    if total < n:
        raise ValueError(f"Not enough stimuli with r_score on disk: have {total}, need {n}.")
    if total == n:
        return items

    # Evenly spaced, monotone-increasing indices without duplicates.
    step = (total - 1) / (n - 1)
    idxs = []
    prev = -1
    for i in range(n):
        idx = int(round(i * step))
        if idx <= prev:
            idx = prev + 1
        if idx > total - 1:
            idx = total - 1
        idxs.append(idx)
        prev = idx

    # If we clamped at the end, backfill to keep length n unique.
    for k in range(n - 1, -1, -1):
        if k == 0:
            break
        if idxs[k] <= idxs[k - 1]:
            idxs[k - 1] = idxs[k] - 1

    selected = [items[i] for i in idxs]
    return selected


def stats_tuple(rs):
    mu = sum(rs) / len(rs)
    return (min(rs), max(rs), float(mu), float(median(rs)))


def cost(rs_a, rs_b):
    a = stats_tuple(rs_a)
    b = stats_tuple(rs_b)
    return sum((x - y) ** 2 for x, y in zip(a, b))


def init_partition(items, target_size, init_method='snake', seed=0):
    # items: list[(stimulus_number, r_score)] length 2*target_size
    if len(items) != 2 * target_size:
        raise ValueError(f"Expected {2 * target_size} items, got {len(items)}")

    idx_sorted = sorted(range(len(items)), key=lambda i: items[i][1])
    if init_method == 'random':
        rng = random.Random(seed)
        idxs = list(range(len(items)))
        rng.shuffle(idxs)
        A = set(idxs[:target_size])
        B = set(idxs[target_size:])
        return A, B

    # 'snake' for 2 groups:
    # take sorted indices in pairs; alternate assignment direction per pair
    A = set()
    B = set()
    pairs = [idx_sorted[i:i + 2] for i in range(0, len(idx_sorted), 2)]
    for k, pair in enumerate(pairs):
        if len(pair) < 2:
            # shouldn't happen since len is even
            A.add(pair[0])
            continue
        if k % 2 == 0:
            A.add(pair[0]); B.add(pair[1])
        else:
            A.add(pair[1]); B.add(pair[0])

    # safety: enforce exact sizes (should already be exact)
    if len(A) != target_size or len(B) != target_size:
        raise RuntimeError(f"Init produced sizes A={len(A)} B={len(B)} (expected {target_size}/{target_size})")
    return A, B


def optimize_two_groups(items, target_size=75, iterations=200000, seed=0, init_method='snake'):
    rng = random.Random(seed)
    rs = [r for _, r in items]

    A, B = init_partition(items, target_size, init_method=init_method, seed=seed)
    current_cost = cost([rs[i] for i in A], [rs[i] for i in B])
    best_cost = current_cost
    bestA = set(A)
    bestB = set(B)

    T0 = 1.0
    for it in range(iterations):
        T = T0 * (1.0 - (it / iterations))
        i = rng.choice(tuple(A))
        j = rng.choice(tuple(B))

        # swap i and j
        A2 = set(A); B2 = set(B)
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
                bestA = set(A)
                bestB = set(B)

    groupA = [items[i] for i in sorted(bestA)]
    groupB = [items[i] for i in sorted(bestB)]
    return groupA, groupB


def write_mapping_csv(out_root, folder_a, folder_b, group_a, group_b):
    a_path = out_root / folder_a[0] / folder_a[1]
    b_path = out_root / folder_b[0] / folder_b[1]
    # Save mappings at repo root so they're easy to find.
    a_csv = ROOT / f"mapping_{folder_a[0]}_{folder_a[1]}.csv"
    b_csv = ROOT / f"mapping_{folder_b[0]}_{folder_b[1]}.csv"
    with open(a_csv, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['stimulus_number', 'r_score', 'relative_wav_path'])
        for stim_num, r_score in group_a:
            rel = os.path.join('audio_stimuli', folder_a[0], folder_a[1], f'{stim_num}.wav')
            w.writerow([stim_num, r_score, rel])
    with open(b_csv, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['stimulus_number', 'r_score', 'relative_wav_path'])
        for stim_num, r_score in group_b:
            rel = os.path.join('audio_stimuli', folder_b[0], folder_b[1], f'{stim_num}.wav')
            w.writerow([stim_num, r_score, rel])
    return a_path, b_path


def copy_group(src_dir, out_dir, group):
    out_dir.mkdir(parents=True, exist_ok=True)
    for stim_num, _r in group:
        src = src_dir / f'chunk_{stim_num}.wav'
        if not src.exists():
            raise FileNotFoundError(f"Missing file: {src}")
        shutil.copy2(src, out_dir / f'{stim_num}.wav')


def print_group_stats(label, group):
    rs = [r for _, r in group]
    s = stats_tuple(rs)
    print(f"{label}: n={len(rs)} min={s[0]:.6f} max={s[1]:.6f} mean={s[2]:.6f} median={s[3]:.6f}")


def main():
    out_root = OUT_ROOT
    make_output_dirs()

    high_df = load_csv(HIGH_CSV)
    low_df = load_csv(LOW_CSV)
    high_avail = get_available_files(HIGH_DIR)
    low_avail = get_available_files(LOW_DIR)

    print(f"High pool available: {len(high_avail)} files")
    print(f"Low pool available: {len(low_avail)} files")
    print(f"Selecting {SELECT_PER_POOL_OPT} items per pool")
    print(f"Init method: {INIT_METHOD} | iterations: {ITERATIONS}")

    high_items = select_evenly_by_r(high_df, high_avail, SELECT_PER_POOL_OPT)
    low_items = select_evenly_by_r(low_df, low_avail, SELECT_PER_POOL_OPT)

    high_A, high_B = optimize_two_groups(
        high_items,
        target_size=TARGET_SIZE,
        iterations=ITERATIONS,
        seed=SEED_HIGH,
        init_method=INIT_METHOD,
    )
    low_A, low_B = optimize_two_groups(
        low_items,
        target_size=TARGET_SIZE,
        iterations=ITERATIONS,
        seed=SEED_LOW,
        init_method=INIT_METHOD,
    )

    # Mapping
    full_targets = ('full_sentence', 'targets')
    imag_targets = ('imagined_sentence', 'targets')
    full_distr = ('full_sentence', 'distractors')
    imag_distr = ('imagined_sentence', 'distractors')

    out_full_targets, out_imag_targets = write_mapping_csv(out_root, full_targets, imag_targets, high_A, high_B)
    out_full_distr, out_imag_distr = write_mapping_csv(out_root, full_distr, imag_distr, low_A, low_B)

    copy_group(HIGH_DIR, out_full_targets, high_A)
    copy_group(HIGH_DIR, out_imag_targets, high_B)
    copy_group(LOW_DIR, out_full_distr, low_A)
    copy_group(LOW_DIR, out_imag_distr, low_B)

    print_group_stats('full_sentence/targets', high_A)
    print_group_stats('imagined_sentence/targets', high_B)
    print_group_stats('full_sentence/distractors', low_A)
    print_group_stats('imagined_sentence/distractors', low_B)

    print(f"Done. Output root: {out_root}")


if __name__ == '__main__':
    main()
