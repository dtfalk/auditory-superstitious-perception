"""
Forced Alignment using Montreal Forced Aligner (MFA) - Multiple Runs Version

MFA is the gold standard for phonetic research. It provides phoneme-level
alignment using acoustic models trained on speech corpora.

=============================================================================
FULL SETUP (run these commands in order)
=============================================================================

1. Create conda environment with MFA:
    conda create -n mfa -c conda-forge montreal-forced-aligner -y

2. Activate it:
    conda activate mfa

3. Download the acoustic model and dictionary:
    mfa model download acoustic english_us_arpa
    mfa model download dictionary english_us_arpa

4. Run the script:
    cd other\audio_helpers\forced_alignment
    python align_with_mfa.py

=============================================================================
"""

import os
import sys
import subprocess
import json
import tempfile
import shutil
import time
import re

# =============================================================================
# CONFIGURATION - EDIT THESE
# =============================================================================

N_RUNS = 10  # Number of times to run alignment
TARGET_WORD = "wall"

# The transcript for fullsentence.wav - EDIT THIS if different
FULLSENTENCE_TRANSCRIPT = "The picture hung on the wall"

# =============================================================================
# PATHS
# =============================================================================

AUDIO_STIMULI_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "audio_stimuli")
OUTPUT_BASE_DIR = os.path.join(os.path.dirname(__file__), "results")
OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "mfa")

# =============================================================================


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def check_mfa_installed():
    """Check if MFA is installed and accessible."""
    try:
        result = subprocess.run(
            ["mfa", "version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"  MFA version: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("ERROR: MFA not found in PATH")
    print("\nTo install MFA:")
    print("  1. Install conda/miniconda from https://docs.conda.io/en/latest/miniconda.html")
    print("  2. Run: conda create -n mfa -c conda-forge montreal-forced-aligner")
    print("  3. Run: conda activate mfa")
    print("  4. Run: mfa model download acoustic english_us_arpa")
    print("  5. Run: mfa model download dictionary english_us_arpa")
    print("\nThen run this script again with the mfa conda environment activated.")
    return False


def create_transcript_file(audio_path, transcript, temp_dir):
    """Create a transcript file in the format MFA expects."""
    audio_basename = os.path.splitext(os.path.basename(audio_path))[0]
    
    # Copy audio to temp dir
    audio_dest = os.path.join(temp_dir, os.path.basename(audio_path))
    shutil.copy2(audio_path, audio_dest)
    
    # Create transcript file
    transcript_path = os.path.join(temp_dir, f"{audio_basename}.txt")
    with open(transcript_path, 'w', encoding='utf-8') as f:
        f.write(transcript)
    
    return temp_dir


def run_mfa_align(input_dir, output_dir, acoustic_model="english_us_arpa", dictionary="english_us_arpa"):
    """Run MFA alignment on a directory of audio files."""
    cmd = [
        "mfa", "align",
        input_dir,
        dictionary,
        acoustic_model,
        output_dir,
        "--clean",
        "--overwrite"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return False
    
    return True


def _parse_tier(content, tier_name, alt_tier_name=None):
    """Parse a single tier from a TextGrid file."""
    tier_match = re.search(
        rf'name\s*=\s*"{tier_name}".*?intervals:\s*size\s*=\s*(\d+)(.*?)(?=item\s*\[|$)',
        content,
        re.IGNORECASE | re.DOTALL
    )

    if not tier_match and alt_tier_name:
        tier_match = re.search(
            rf'name\s*=\s*"{alt_tier_name}".*?intervals:\s*size\s*=\s*(\d+)(.*?)(?=item\s*\[|$)',
            content,
            re.IGNORECASE | re.DOTALL
        )

    items = []
    if tier_match:
        intervals_text = tier_match.group(2)
        interval_pattern = r'intervals\s*\[\d+\].*?xmin\s*=\s*([\d.]+).*?xmax\s*=\s*([\d.]+).*?text\s*=\s*"([^"]*)"'

        for match in re.finditer(interval_pattern, intervals_text, re.DOTALL):
            xmin, xmax, text = match.groups()
            xmin, xmax = float(xmin), float(xmax)
            if text.strip():
                items.append({
                    "label": text.strip(),
                    "start": xmin,
                    "end": xmax,
                    "duration": xmax - xmin
                })
    return items


def parse_textgrid_robust(textgrid_path):
    """Robust TextGrid parser — extracts both words and phones tiers."""
    with open(textgrid_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # --- words tier ---
    raw_words = _parse_tier(content, "words", alt_tier_name="word")
    words = [{
        "word": w["label"],
        "start": w["start"],
        "end": w["end"],
        "duration": w["duration"]
    } for w in raw_words]

    # --- phones tier ---
    phones = _parse_tier(content, "phones", alt_tier_name="phone")

    # Associate each phone with its parent word
    for w in words:
        w["phones"] = [
            {"phone": p["label"], "start": p["start"],
             "end": p["end"], "duration": p["duration"]}
            for p in phones
            if p["start"] >= w["start"] - 1e-6 and p["end"] <= w["end"] + 1e-6
        ]

    return words


def find_word(words, target_word):
    """Find a specific word in the alignment results."""
    target_lower = target_word.lower().strip()
    for w in words:
        if target_lower in w.get("word", "").lower():
            return w
    return None


def save_results(data, output_path):
    """Save alignment results to JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def run_single_alignment(audio_path, transcript, run_number, audio_name):
    """Run a single MFA alignment."""
    print(f"  Run {run_number}: Aligning {os.path.basename(audio_path)}...", end=" ", flush=True)
    
    start_time = time.time()
    
    # Create temp directories
    temp_input = tempfile.mkdtemp(prefix="mfa_input_")
    temp_output = tempfile.mkdtemp(prefix="mfa_output_")
    
    try:
        create_transcript_file(audio_path, transcript, temp_input)
        
        if run_mfa_align(temp_input, temp_output):
            textgrid_path = os.path.join(temp_output, f"{audio_name}.TextGrid")
            
            if os.path.exists(textgrid_path):
                words = parse_textgrid_robust(textgrid_path)
                elapsed = time.time() - start_time
                print(f"done ({elapsed:.2f}s)")
                return words
        
        elapsed = time.time() - start_time
        print(f"failed ({elapsed:.2f}s)")
        return None
        
    finally:
        # Clean up temp directories
        if os.path.exists(temp_input):
            shutil.rmtree(temp_input)
        if os.path.exists(temp_output):
            shutil.rmtree(temp_output)


def run_multiple_alignments(audio_path, transcript, n_runs, audio_name):
    """Run alignment n_runs times and collect results."""
    all_runs = []
    
    for run_idx in range(n_runs):
        words = run_single_alignment(audio_path, transcript, run_idx + 1, audio_name)
        
        if words is None:
            continue
        
        target_info = find_word(words, TARGET_WORD)
        
        run_data = {
            "run": run_idx + 1,
            "words": words,
            "target_word": TARGET_WORD,
            "target_timing": target_info
        }
        
        all_runs.append(run_data)
        
        # Save individual run
        run_file = os.path.join(OUTPUT_DIR, f"{audio_name}_run_{run_idx + 1:02d}.json")
        save_results(run_data, run_file)
    
    return all_runs


def calculate_statistics(all_runs):
    """Calculate statistics across all runs for the target word."""
    starts = []
    ends = []
    durations = []
    
    for run in all_runs:
        if run["target_timing"]:
            starts.append(run["target_timing"]["start"] * 1000)
            ends.append(run["target_timing"]["end"] * 1000)
            durations.append(run["target_timing"]["duration"] * 1000)
    
    if not starts:
        return None
    
    n = len(starts)
    
    def calc_stats(values):
        mean = sum(values) / n
        return {
            "mean": mean,
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
            "std": (sum((x - mean)**2 for x in values) / n) ** 0.5,
            "values": values
        }
    
    result = {
        "n_successful_runs": n,
        "target_word": TARGET_WORD,
        "start_ms": calc_stats(starts),
        "end_ms": calc_stats(ends),
        "duration_ms": calc_stats(durations)
    }

    # Include phoneme data from the first successful run
    for run in all_runs:
        if run["target_timing"] and "phones" in run["target_timing"]:
            result["phones"] = run["target_timing"]["phones"]
            break

    return result


def print_statistics(stats, title):
    """Print statistics in a nice format."""
    if not stats:
        print(f"\n  No statistics available (target word not found)")
        return
    
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    
    print(f"\n  Successful runs: {stats['n_successful_runs']} / {N_RUNS}")
    print(f"  Target word: '{stats['target_word']}'")
    
    for metric_name, metric_key in [("Start Time", "start_ms"), ("End Time", "end_ms"), ("Duration", "duration_ms")]:
        m = stats[metric_key]
        print(f"\n  {metric_name}:")
        print(f"    Mean:  {m['mean']:>8.2f} ms")
        print(f"    Std:   {m['std']:>8.2f} ms")
        print(f"    Range: {m['range']:>8.2f} ms (min: {m['min']:.2f}, max: {m['max']:.2f})")
    
    # Print phoneme breakdown if available
    if "phones" in stats:
        print(f"\n  Phoneme breakdown (run 1):")
        for p in stats["phones"]:
            print(f"    /{p['phone']}/  {p['start']*1000:>8.1f} – {p['end']*1000:>8.1f} ms  ({p['duration']*1000:.1f} ms)")
    
    print()


def main():
    print("="*70)
    print("  MONTREAL FORCED ALIGNER (MFA) - MULTIPLE RUNS")
    print("="*70)
    print(f"\n  Configuration:")
    print(f"    N_RUNS: {N_RUNS}")
    print(f"    Target: '{TARGET_WORD}'")
    
    # Check MFA is installed
    print("\n  Checking MFA installation...")
    if not check_mfa_installed():
        return
    
    ensure_output_dir()
    
    # Files to analyze
    fullsentence_path = os.path.join(AUDIO_STIMULI_DIR, "fullsentence.wav")
    
    # Check files exist
    if not os.path.exists(fullsentence_path):
        print(f"ERROR: Could not find {fullsentence_path}")
        return
    
    # Run alignments on fullsentence
    print(f"\n{'-'*70}")
    print(f"  Analyzing: fullsentence.wav ({N_RUNS} runs)")
    print(f"  Transcript: \"{FULLSENTENCE_TRANSCRIPT}\"")
    print(f"{'-'*70}")
    
    all_runs_fullsentence = run_multiple_alignments(
        fullsentence_path, FULLSENTENCE_TRANSCRIPT, N_RUNS, "fullsentence"
    )
    
    stats_fullsentence = calculate_statistics(all_runs_fullsentence)
    print_statistics(stats_fullsentence, "FULLSENTENCE.WAV - WITHIN-METHOD CONSISTENCY")
    
    # Save summary
    summary = {
        "tool": "mfa",
        "n_runs": N_RUNS,
        "audio_file": "fullsentence.wav",
        "transcript": FULLSENTENCE_TRANSCRIPT,
        "statistics": stats_fullsentence,
        "all_runs": all_runs_fullsentence
    }
    save_results(summary, os.path.join(OUTPUT_DIR, "fullsentence_summary.json"))
    
    print(f"\n{'='*70}")
    print(f"  MFA ALIGNMENT COMPLETE")
    print(f"  Results saved to: {OUTPUT_DIR}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
