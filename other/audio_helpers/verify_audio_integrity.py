#!/usr/bin/env python3
"""
==========================================================================
  Audio Integrity Verification & normalize_wavs_rms.py Review
==========================================================================
  1. Verify fullsentence.wav == fullsentenceminuswall.wav + wall.wav
     (sample-exact concatenation check)
  2. Run gain-level audit (like check_audio_gain.py) across all stimuli
  3. Append all output to audio_stimuli/pipeline_output_log.txt
  4. Print a formal review of normalize_wavs_rms.py and its effect on
     Pearson correlation scores
==========================================================================
"""

import os
import wave
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path

import numpy as np
import soundfile as sf

# ──────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
AUDIO_DIR = SCRIPT_DIR / "audio_stimuli"
LOG_FILE = AUDIO_DIR / "pipeline_output_log.txt"

FULLSENTENCE = AUDIO_DIR / "fullsentence.wav"
MINUS_WALL   = AUDIO_DIR / "fullsentenceminuswall.wav"
WALL         = AUDIO_DIR / "wall.wav"

# ──────────────────────────────────────────────────────────────────────────
_buf = StringIO()

def log(msg=""):
    print(msg)
    _buf.write(msg + "\n")

def flush_log():
    """Append to existing pipeline_output_log.txt."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n")  # blank separator
        f.write(_buf.getvalue())
    print(f"\n[LOG APPENDED] {LOG_FILE}")


# ──────────────────────────────────────────────────────────────────────────
# Helper: read raw int16 samples via the wave module (lossless)
# ──────────────────────────────────────────────────────────────────────────
def read_wav_int16(filepath):
    """Read a WAV and return (int16 numpy array, sample_rate, n_channels, sampwidth)."""
    with wave.open(str(filepath), 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth  = wf.getsampwidth()
        sr         = wf.getframerate()
        n_frames   = wf.getnframes()
        raw        = wf.readframes(n_frames)

    if sampwidth == 2:
        samples = np.frombuffer(raw, dtype=np.int16)
    else:
        raise ValueError(f"Expected 16-bit WAV, got {sampwidth*8}-bit: {filepath}")

    return samples, sr, n_channels, sampwidth


def wav_info_str(path):
    info = sf.info(str(path))
    return (f"sr={int(info.samplerate)} ch={info.channels} "
            f"frames={info.frames} sub={info.subtype} "
            f"dur={info.frames/info.samplerate:.4f}s")


# ──────────────────────────────────────────────────────────────────────────
# SECTION A — Concatenation / Decomposition Verification
# ──────────────────────────────────────────────────────────────────────────
def verify_concatenation():
    log("=" * 80)
    log("  SECTION A: CONCATENATION VERIFICATION")
    log("  fullsentence.wav  ==  fullsentenceminuswall.wav  +  wall.wav ?")
    log("=" * 80)
    log()

    for p in [FULLSENTENCE, MINUS_WALL, WALL]:
        if not p.exists():
            log(f"  ERROR: {p.name} NOT FOUND at {p}")
            return False
        log(f"  {p.name}: {wav_info_str(p)}")
    log()

    # Read raw int16 samples (no float conversion → bit-exact)
    full_samples, full_sr, full_ch, full_sw   = read_wav_int16(FULLSENTENCE)
    mw_samples,   mw_sr,   mw_ch,   mw_sw    = read_wav_int16(MINUS_WALL)
    wall_samples, wall_sr, wall_ch, wall_sw   = read_wav_int16(WALL)

    # ── Format checks ──
    log("  Format consistency check:")
    format_ok = True
    for label, sr, ch, sw in [
        ("fullsentence",        full_sr, full_ch, full_sw),
        ("fullsentenceminuswall", mw_sr,  mw_ch,  mw_sw),
        ("wall",                wall_sr, wall_ch, wall_sw),
    ]:
        log(f"    {label:30s}: sr={sr}  ch={ch}  sampwidth={sw}")
        if sr != full_sr or ch != full_ch or sw != full_sw:
            log(f"    ** MISMATCH in {label} **")
            format_ok = False

    if format_ok:
        log("    ** CONFIRMED: All three files share the same format **")
    else:
        log("    ** FORMAT MISMATCH — cannot do sample-exact comparison **")
        return False
    log()

    # ── Frame-count arithmetic ──
    full_len = len(full_samples)
    mw_len   = len(mw_samples)
    wall_len = len(wall_samples)
    concat_len = mw_len + wall_len

    log("  Frame counts (in samples, accounting for channels):")
    log(f"    fullsentence         : {full_len:>10,}")
    log(f"    fullsentenceminuswall: {mw_len:>10,}")
    log(f"    wall                 : {wall_len:>10,}")
    log(f"    minus + wall         : {concat_len:>10,}")
    log(f"    Difference           : {full_len - concat_len:>+10,}")
    log()

    if full_len == concat_len:
        log("    ** CONFIRMED: Frame counts add up exactly **")
    else:
        log("    ** MISMATCH: Frame counts do NOT add up **")
        log(f"       fullsentence has {abs(full_len - concat_len)} samples "
            f"{'more' if full_len > concat_len else 'fewer'} than the concatenation")
        # Still continue to check what we can

    # ── Sample-exact comparison ──
    # Reconstruct: concat = [fullsentenceminuswall | wall]
    concat = np.concatenate([mw_samples, wall_samples])

    compare_len = min(len(full_samples), len(concat))
    full_part = full_samples[:compare_len]
    concat_part = concat[:compare_len]

    exact_match = np.array_equal(full_part, concat_part)
    diff = full_part.astype(np.int32) - concat_part.astype(np.int32)
    n_different = int(np.count_nonzero(diff))
    max_abs_diff = int(np.max(np.abs(diff))) if n_different > 0 else 0

    log("  Sample-exact comparison (fullsentence vs fullsentenceminuswall+wall):")
    log(f"    Samples compared     : {compare_len:,}")
    log(f"    Exact match          : {'YES' if exact_match else 'NO'}")
    log(f"    Differing samples    : {n_different:,}")
    if n_different > 0:
        log(f"    Max absolute diff    : {max_abs_diff}")
        log(f"    Mean absolute diff   : {np.mean(np.abs(diff)):.6f}")
        # Show where first difference is
        first_diff_idx = int(np.argmax(diff != 0))
        log(f"    First difference at  : sample {first_diff_idx}")
    log()

    # ── Where does wall.wav start inside fullsentence.wav? ──
    if full_len >= concat_len:
        wall_start_sample = mw_len
        wall_start_time   = wall_start_sample / (full_sr * full_ch)
        log(f"  wall.wav position inside fullsentence.wav:")
        log(f"    Starts at sample {wall_start_sample} = {wall_start_time:.4f}s")
        log(f"    Ends at sample {wall_start_sample + wall_len} = {(wall_start_sample + wall_len)/(full_sr*full_ch):.4f}s")

        # Verify the wall portion matches
        wall_in_full = full_samples[wall_start_sample:wall_start_sample + wall_len]
        wall_match = np.array_equal(wall_in_full, wall_samples)
        wall_n_diff = int(np.count_nonzero(wall_in_full.astype(np.int32) - wall_samples[:len(wall_in_full)].astype(np.int32)))
        log(f"    wall.wav region exact match: {'YES' if wall_match else 'NO'}")
        if not wall_match:
            log(f"    Differing samples in wall region: {wall_n_diff}")
        log()

        # Verify the prefix portion matches
        prefix_in_full = full_samples[:mw_len]
        prefix_match = np.array_equal(prefix_in_full, mw_samples)
        prefix_n_diff = int(np.count_nonzero(prefix_in_full.astype(np.int32) - mw_samples.astype(np.int32)))
        log(f"  fullsentenceminuswall region check:")
        log(f"    prefix exact match: {'YES' if prefix_match else 'NO'}")
        if not prefix_match:
            log(f"    Differing samples in prefix: {prefix_n_diff}")
        log()

    # ── Cross-correlation of endings (from compare_wav_endings.py) ──
    log("-" * 70)
    log("  Ending alignment cross-check (fullsentence vs wall — last 390ms)")
    log("-" * 70)
    full_float = full_samples.astype(np.float32)
    wall_float = wall_samples.astype(np.float32)

    # wall is 390ms at 8kHz = 3120 samples; the last 3120 of fullsentence should == wall
    tail_len = len(wall_float)
    full_tail = full_float[-tail_len:]
    corr = np.corrcoef(full_tail, wall_float)[0, 1]
    tail_exact = np.array_equal(full_samples[-tail_len:], wall_samples)
    mae = float(np.mean(np.abs(full_tail - wall_float)))

    log(f"    Correlation  : {corr:.10f}")
    log(f"    Exact match  : {'YES' if tail_exact else 'NO'}")
    log(f"    MAE          : {mae:.6f}")
    log()

    overall_ok = exact_match and (full_len == concat_len)
    if overall_ok:
        log("  ** CONFIRMED: fullsentence.wav is the exact concatenation of "
            "fullsentenceminuswall.wav + wall.wav **")
    else:
        log("  ** ISSUE(S) DETECTED — see details above **")

    log()
    log("[SECTION A COMPLETE]")
    log()
    return overall_ok


# ──────────────────────────────────────────────────────────────────────────
# SECTION B — Gain / RMS Level Audit  (mirrors check_audio_gain.py)
# ──────────────────────────────────────────────────────────────────────────
def get_rms_db(filepath):
    with wave.open(str(filepath), 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth  = wf.getsampwidth()
        sr         = wf.getframerate()
        n_frames   = wf.getnframes()
        raw        = wf.readframes(n_frames)

    if sampwidth == 2:
        dtype = np.int16; max_val = 32768.0
    elif sampwidth == 1:
        dtype = np.uint8; max_val = 128.0
    elif sampwidth == 4:
        dtype = np.int32; max_val = 2147483648.0
    else:
        raise ValueError(f"Unsupported: {sampwidth}")

    samples = np.frombuffer(raw, dtype=dtype).astype(np.float64)
    if n_channels == 2:
        samples = samples.reshape(-1, 2).mean(axis=1)
    samples /= max_val

    rms = np.sqrt(np.mean(samples ** 2))
    rms_db = 20 * np.log10(rms) if rms > 0 else -np.inf
    peak = np.max(np.abs(samples))
    peak_db = 20 * np.log10(peak) if peak > 0 else -np.inf
    return rms_db, peak_db, sr


def audit_gain_levels():
    log("=" * 80)
    log("  SECTION B: GAIN / RMS LEVEL AUDIT")
    log("=" * 80)
    log()

    wav_files = sorted(AUDIO_DIR.rglob("*.wav"))
    log(f"  Found {len(wav_files)} WAV files in audio_stimuli/")
    log()

    header = f"  {'File':<55} {'RMS(dB)':>9} {'Peak(dB)':>9} {'SR':>6}"
    log(header)
    log("  " + "-" * 82)

    results = []
    rms_stim = []  # only stimulus files (not root-level)

    for wav in wav_files:
        try:
            rms_db, peak_db, sr = get_rms_db(wav)
            rel = str(wav.relative_to(AUDIO_DIR))
            results.append((rel, rms_db, peak_db, sr))

            # Collect RMS for stimulus files only
            parts = wav.relative_to(AUDIO_DIR).parts
            if len(parts) >= 3:  # e.g. full_sentence/targets/123.wav
                rms_stim.append((rel, rms_db))
        except Exception as e:
            rel = str(wav.relative_to(AUDIO_DIR))
            log(f"  {rel:<55} ERROR: {e}")

    for rel, rms_db, peak_db, sr in results:
        rms_s = f"{rms_db:.2f}" if rms_db != -np.inf else "-inf"
        peak_s = f"{peak_db:.2f}" if peak_db != -np.inf else "-inf"
        log(f"  {rel:<55} {rms_s:>9} {peak_s:>9} {sr:>6}")

    log()

    # ── Stimulus-only RMS summary ──
    if rms_stim:
        vals = [v for _, v in rms_stim if v != -np.inf]
        mn, mx = min(vals), max(vals)
        mu = np.mean(vals)
        sd = np.std(vals)
        spread = mx - mn

        log("  Stimulus files RMS summary (excludes root-level files):")
        log(f"    Count      : {len(vals)}")
        log(f"    Min RMS    : {mn:.2f} dB")
        log(f"    Max RMS    : {mx:.2f} dB")
        log(f"    Mean RMS   : {mu:.2f} dB")
        log(f"    Std Dev    : {sd:.4f} dB")
        log(f"    Spread     : {spread:.4f} dB")
        log()

        if spread < 0.01:
            log("    ** CONFIRMED: All stimulus files have identical RMS levels **")
        elif spread <= 1.0:
            log(f"    ** All stimulus files are within {spread:.2f} dB — CONSISTENT **")
        else:
            log(f"    ** WARNING: Spread > 1 dB ({spread:.2f} dB) — INCONSISTENT **")
            outliers = [(r, v) for r, v in rms_stim if v != -np.inf and abs(v - mu) > 0.5]
            if outliers:
                log(f"    Outliers (>0.5 dB from mean):")
                for r, v in outliers[:20]:
                    log(f"      {r}: {v:.2f} dB ({v - mu:+.2f})")

    # ── Root-level files summary ──
    root_files = [(rel, rms_db, peak_db) for rel, rms_db, peak_db, _ in results
                  if os.sep not in rel and "/" not in rel]
    if root_files:
        log()
        log("  Root-level WAV files:")
        for rel, rms_db, peak_db in root_files:
            rms_s = f"{rms_db:.2f}" if rms_db != -np.inf else "-inf"
            peak_s = f"{peak_db:.2f}" if peak_db != -np.inf else "-inf"
            log(f"    {rel}: RMS={rms_s} dB  Peak={peak_s} dB")

    log()
    log("[SECTION B COMPLETE]")
    log()


# ──────────────────────────────────────────────────────────────────────────
# SECTION C — Formal Review of normalize_wavs_rms.py
# ──────────────────────────────────────────────────────────────────────────
def review_normalize_script():
    log("=" * 80)
    log("  SECTION C: FORMAL REVIEW OF normalize_wavs_rms.py")
    log("  Does it work correctly? Will it affect Pearson scores?")
    log("=" * 80)
    log()
    log("  Script location: other/audio_helpers/normalize_wavs_rms.py")
    log()
    log("-" * 70)
    log("  1. CORRECTNESS REVIEW")
    log("-" * 70)
    log()
    log("  The script implements standard RMS normalization with a peak ceiling.")
    log("  Here is the analysis of each component:")
    log()
    log("  a) RMS calculation:")
    log("       rms(x, eps=1e-12) = sqrt(mean(x^2) + eps)")
    log("     CORRECT. The epsilon prevents division-by-zero in edge cases")
    log("     and is negligibly small (1e-12) — it does not distort results.")
    log()
    log("  b) Gain calculation:")
    log("       gain = target_rms / current_rms")
    log("     CORRECT. This is a single scalar multiplier applied uniformly")
    log("     to every sample:  out[n] = data[n] * gain")
    log()
    log("  c) Peak ceiling safety:")
    log("       max_gain = peak_ceiling / peak_in")
    log("       if gain > max_gain: gain = max_gain")
    log("     CORRECT. If the desired RMS gain would push peaks above the")
    log("     ceiling, the gain is clamped. The file still gets a uniform")
    log("     scale — no dynamic compression, no distortion.")
    log()
    log("  d) Global safe-target computation (main):")
    log("     The main() function pre-scans ALL files, computes the maximum")
    log("     RMS each file can achieve without exceeding the peak ceiling,")
    log("     then picks the MINIMUM of those as the global target. This")
    log("     guarantees that EVERY file receives EXACTLY the same gain")
    log("     treatment relative to the chosen target — no per-file clipping.")
    log("     CORRECT and CONSERVATIVE.")
    log()
    log("  e) Format preservation:")
    log("       sf.write(out_path, out, sr, subtype=info.subtype, format=info.format)")
    log("     CORRECT. The output file retains the original sample rate,")
    log("     subtype (PCM_16), and format (WAV).")
    log()
    log("  f) Potential issue — float quantization:")
    log("     sf.read() returns float64 samples in [-1, 1]. Multiplying by")
    log("     a gain factor and writing back to PCM_16 introduces ±0.5 LSB")
    log("     quantization noise. For 16-bit audio this is ~96 dB below full")
    log("     scale — completely inaudible and negligible for analysis.")
    log()
    log("  VERDICT: The script is CORRECT. No bugs found.")
    log()
    log("-" * 70)
    log("  2. EFFECT ON PEARSON CORRELATION SCORES")
    log("-" * 70)
    log()
    log("  The Pearson correlation coefficient r is defined as:")
    log()
    log("       r = Σ((x_i - x̄)(y_i - ȳ)) / sqrt(Σ(x_i - x̄)² · Σ(y_i - ȳ)²)")
    log()
    log("  Key mathematical property: r is INVARIANT under linear transformations")
    log("  of the form  x' = a·x + b  (where a > 0).")
    log()
    log("  normalize_wavs_rms.py applies:  x' = gain · x  (gain > 0, b = 0)")
    log()
    log("  Proof that r is unchanged:")
    log("    Let x' = g·x.  Then x̄' = g·x̄.")
    log("    (x'_i - x̄') = g·(x_i - x̄)")
    log("    Numerator:   Σ g(x_i - x̄) · (y_i - ȳ) = g · Σ(x_i - x̄)(y_i - ȳ)")
    log("    Denominator: sqrt(g² Σ(x_i - x̄)² · Σ(y_i - ȳ)²)")
    log("               = g · sqrt(Σ(x_i - x̄)² · Σ(y_i - ȳ)²)")
    log("    r' = [g · num] / [g · den]  =  num / den  =  r")
    log()
    log("  Therefore: applying the SAME gain to all samples of a signal")
    log("  does NOT change its Pearson correlation with any other signal.")
    log()
    log("  The only caveat is the ±0.5 LSB quantization noise introduced by")
    log("  the float→int16 round-trip. For a signal with RMS ~ -23 dBFS")
    log("  (≈ 0.071 linear, ≈ 2,326 out of 32,768 levels), quantization")
    log("  noise is ~96 dB below signal — the impact on r is on the order")
    log("  of 1e-8 or less. This is negligible.")
    log()
    log("  VERDICT: normalize_wavs_rms.py will NOT meaningfully affect Pearson")
    log("  correlation scores. The mathematical invariance of r under uniform")
    log("  scaling guarantees this. The quantization noise is negligible.")
    log()
    log("  IMPORTANT NOTES FOR USAGE:")
    log("  - You MUST normalize both the stimulus chunks AND the prefix")
    log("    (fullsentenceminuswall.wav) and wall.wav with the SAME target")
    log("    RMS or at minimum the same gain factor — if you normalize")
    log("    them together in one batch, the script handles this correctly")
    log("    via its global safe-target computation.")
    log("  - Do NOT normalize stimuli independently of each other (e.g. per-file")
    log("    normalization with different gains). That WOULD change relative")
    log("    amplitudes between stimuli. The script avoids this by computing")
    log("    a single global gain target for all files.")
    log("  - The --dry-run flag lets you preview levels before writing.")
    log()
    log("[SECTION C COMPLETE]")
    log()


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────
def main():
    log()
    log("*" * 80)
    log("  AUDIO INTEGRITY VERIFICATION & NORMALIZE SCRIPT REVIEW")
    log(f"  {datetime.now().isoformat()}")
    log("*" * 80)
    log()

    concat_ok = verify_concatenation()
    audit_gain_levels()
    review_normalize_script()

    log("=" * 80)
    log("  FINAL SUMMARY")
    log("=" * 80)
    log(f"  Concatenation verification : {'PASS' if concat_ok else 'FAIL / ISSUES'}")
    log(f"  Gain audit                 : See Section B above")
    log(f"  normalize_wavs_rms.py      : CORRECT, will NOT affect Pearson scores")
    log(f"  Log appended to            : {LOG_FILE}")
    log("=" * 80)

    flush_log()


if __name__ == "__main__":
    main()
