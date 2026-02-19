"""
Forced Alignment using Gentle - Multiple Runs Version

Gentle is a robust forced aligner built on Kaldi. It handles disfluencies
and various audio qualities well.

Installation (Docker - recommended):
    1. Install Docker Desktop: https://www.docker.com/products/docker-desktop
    2. Pull Gentle image: docker pull lowerquality/gentle
    3. Run Gentle server: docker run -p 8765:8765 lowerquality/gentle

Usage:
    1. Start Gentle server (see above)
    2. python align_with_gentle.py
"""

import os
import sys
import json
import time
import requests

# =============================================================================
# CONFIGURATION - EDIT THESE
# =============================================================================

N_RUNS = 5  # Number of times to run alignment
TARGET_WORD = "wall"

# The transcript for fullsentence.wav - EDIT THIS if different
FULLSENTENCE_TRANSCRIPT = "The picture hung on the wall"

# The transcript for targetwall.wav
TARGETWALL_TRANSCRIPT = "wall"

# Gentle server URL (default Docker configuration)
GENTLE_URL = "http://localhost:8765/transcriptions"

# =============================================================================
# PATHS
# =============================================================================

AUDIO_STIMULI_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "audio_stimuli")
OUTPUT_BASE_DIR = os.path.join(os.path.dirname(__file__), "results")
OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "gentle")

# =============================================================================


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def check_gentle_running():
    """Check if Gentle server is running."""
    try:
        response = requests.get("http://localhost:8765/", timeout=5)
        return True
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        return False


def align_with_gentle_single(audio_path, transcript, run_number):
    """Send audio and transcript to Gentle for alignment."""
    print(f"  Run {run_number}: Aligning {os.path.basename(audio_path)}...", end=" ", flush=True)
    
    start_time = time.time()
    
    with open(audio_path, 'rb') as audio_file:
        files = {
            'audio': (os.path.basename(audio_path), audio_file, 'audio/wav')
        }
        data = {
            'transcript': transcript
        }
        
        response = requests.post(
            GENTLE_URL,
            files=files,
            data=data,
            params={'async': 'false'}
        )
    
    elapsed = time.time() - start_time
    print(f"done ({elapsed:.2f}s)")
    
    if response.status_code != 200:
        print(f"ERROR: Gentle returned status {response.status_code}")
        return None
    
    return response.json()


def extract_word_timings(gentle_result):
    """Extract word timings from Gentle result."""
    words = []
    
    for word_info in gentle_result.get("words", []):
        if word_info.get("case") == "success":
            words.append({
                "word": word_info["word"],
                "start": word_info["start"],
                "end": word_info["end"],
                "duration": word_info["end"] - word_info["start"],
                "aligned": True,
                "phones": word_info.get("phones", [])
            })
        else:
            words.append({
                "word": word_info["word"],
                "start": None,
                "end": None,
                "duration": None,
                "aligned": False,
                "phones": []
            })
    
    return words


def find_word(words, target_word):
    """Find a specific word in the alignment results."""
    target_lower = target_word.lower().strip()
    for w in words:
        if target_lower in w.get("word", "").lower() and w.get("aligned"):
            return w
    return None


def save_results(data, output_path):
    """Save alignment results to JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def run_multiple_alignments(audio_path, transcript, n_runs, audio_name):
    """Run alignment n_runs times and collect results."""
    all_runs = []
    
    for run_idx in range(n_runs):
        result = align_with_gentle_single(audio_path, transcript, run_idx + 1)
        if not result:
            continue
        
        words = extract_word_timings(result)
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
    
    return {
        "n_successful_runs": n,
        "target_word": TARGET_WORD,
        "start_ms": calc_stats(starts),
        "end_ms": calc_stats(ends),
        "duration_ms": calc_stats(durations)
    }


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
    
    print()


def main():
    print("="*70)
    print("  GENTLE FORCED ALIGNER - MULTIPLE RUNS")
    print("="*70)
    print(f"\n  Configuration:")
    print(f"    N_RUNS: {N_RUNS}")
    print(f"    Target: '{TARGET_WORD}'")
    
    # Check if Gentle is running
    print("\n  Checking Gentle server...")
    if not check_gentle_running():
        print("\n  ERROR: Gentle server not found at localhost:8765")
        print("\n  To start Gentle with Docker:")
        print("    docker pull lowerquality/gentle")
        print("    docker run -p 8765:8765 lowerquality/gentle")
        return
    
    print("  Gentle server is running!")
    
    ensure_output_dir()
    
    # Files to analyze
    fullsentence_path = os.path.join(AUDIO_STIMULI_DIR, "fullsentence.wav")
    targetwall_path = os.path.join(AUDIO_STIMULI_DIR, "targetwall.wav")
    
    # Check files exist
    if not os.path.exists(fullsentence_path):
        print(f"ERROR: Could not find {fullsentence_path}")
        return
    
    # Run alignments on fullsentence
    print(f"\n{'-'*70}")
    print(f"  Analyzing: fullsentence.wav ({N_RUNS} runs)")
    print(f"{'-'*70}")
    
    all_runs_fullsentence = run_multiple_alignments(
        fullsentence_path, FULLSENTENCE_TRANSCRIPT, N_RUNS, "fullsentence"
    )
    
    stats_fullsentence = calculate_statistics(all_runs_fullsentence)
    print_statistics(stats_fullsentence, "FULLSENTENCE.WAV - WITHIN-METHOD CONSISTENCY")
    
    # Save summary
    summary = {
        "tool": "gentle",
        "n_runs": N_RUNS,
        "audio_file": "fullsentence.wav",
        "transcript": FULLSENTENCE_TRANSCRIPT,
        "statistics": stats_fullsentence,
        "all_runs": all_runs_fullsentence
    }
    save_results(summary, os.path.join(OUTPUT_DIR, "fullsentence_summary.json"))
    
    # Run alignments on targetwall
    if os.path.exists(targetwall_path):
        print(f"\n{'-'*70}")
        print(f"  Analyzing: targetwall.wav ({N_RUNS} runs)")
        print(f"{'-'*70}")
        
        all_runs_targetwall = run_multiple_alignments(
            targetwall_path, TARGETWALL_TRANSCRIPT, N_RUNS, "targetwall"
        )
        
        stats_targetwall = calculate_statistics(all_runs_targetwall)
        print_statistics(stats_targetwall, "TARGETWALL.WAV - WITHIN-METHOD CONSISTENCY")
        
        summary_target = {
            "tool": "gentle",
            "n_runs": N_RUNS,
            "audio_file": "targetwall.wav",
            "transcript": TARGETWALL_TRANSCRIPT,
            "statistics": stats_targetwall,
            "all_runs": all_runs_targetwall
        }
        save_results(summary_target, os.path.join(OUTPUT_DIR, "targetwall_summary.json"))
    
    print(f"\n{'='*70}")
    print(f"  GENTLE ALIGNMENT COMPLETE")
    print(f"  Results saved to: {OUTPUT_DIR}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
