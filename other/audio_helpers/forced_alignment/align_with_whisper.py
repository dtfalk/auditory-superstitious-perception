"""
Forced Alignment using OpenAI Whisper - Multiple Runs Version

Whisper is a general-purpose speech recognition model that can also provide
word-level timestamps. It's the easiest tool to use but may be slightly less
precise than purpose-built forced aligners.

=============================================================================
FULL SETUP (run these commands in order)
=============================================================================

1. Create conda environment:
    conda create -n whisper python=3.10 -y

2. Activate it:
    conda activate whisper

3. Install PyTorch with CUDA 11.8:
    conda install pytorch torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia -y

4. Install Whisper:
    pip install openai-whisper

5. Run the script:
    cd other\audio_helpers\forced_alignment
    python align_with_whisper.py

=============================================================================
"""

import os
import sys
import json
import time

# Check if whisper is installed
try:
    import whisper
except ImportError:
    print("ERROR: openai-whisper not installed")
    print("Install with: pip install openai-whisper")
    sys.exit(1)

# =============================================================================
# CONFIGURATION - EDIT THESE
# =============================================================================

N_RUNS = 10  # Number of times to run alignment
TARGET_WORD = "wall"
MODEL_SIZE = "base"  # "tiny", "base", "small", "medium", "large"

# =============================================================================
# PATHS
# =============================================================================

AUDIO_STIMULI_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "audio_stimuli")
OUTPUT_BASE_DIR = os.path.join(os.path.dirname(__file__), "results")
OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "whisper")

# =============================================================================


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_model():
    """Load Whisper model once."""
    print(f"\n  Loading Whisper model: {MODEL_SIZE}")
    print("  (First run will download the model, ~140MB for 'base')")
    # Force CPU if CUDA isn't compatible (e.g. Blackwell sm_120 with CUDA 11.8 builds)
    import torch
    device = "cpu"
    if torch.cuda.is_available():
        try:
            # Test if CUDA actually works with this GPU
            torch.zeros(1).cuda()
            device = "cuda"
        except Exception:
            print("  Note: CUDA available but GPU not compatible with this PyTorch build, using CPU")
    print(f"  Device: {device}")
    return whisper.load_model(MODEL_SIZE, device=device)


def align_with_whisper_single(model, audio_path, run_number):
    """Run a single alignment."""
    print(f"  Run {run_number}: Aligning {os.path.basename(audio_path)}...", end=" ", flush=True)
    
    start_time = time.time()
    result = model.transcribe(
        audio_path,
        word_timestamps=True,
        language="en"
    )
    elapsed = time.time() - start_time
    print(f"done ({elapsed:.2f}s)")
    
    return result


def extract_word_timings(result):
    """Extract word-level timings from Whisper result."""
    words = []
    
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            words.append({
                "word": word_info["word"].strip(),
                "start": word_info["start"],
                "end": word_info["end"],
                "duration": word_info["end"] - word_info["start"]
            })
    
    return words


def find_word(words, target_word):
    """Find a specific word in the alignment results."""
    target_lower = target_word.lower().strip()
    for w in words:
        if target_lower in w["word"].lower():
            return w
    return None


def save_results(data, output_path):
    """Save alignment results to JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def run_multiple_alignments(model, audio_path, n_runs, audio_name):
    """Run alignment n_runs times and collect results."""
    all_runs = []
    
    for run_idx in range(n_runs):
        result = align_with_whisper_single(model, audio_path, run_idx + 1)
        words = extract_word_timings(result)
        target_info = find_word(words, TARGET_WORD)
        
        run_data = {
            "run": run_idx + 1,
            "transcription": result.get("text", ""),
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
    print("  WHISPER FORCED ALIGNMENT - MULTIPLE RUNS")
    print("="*70)
    print(f"\n  Configuration:")
    print(f"    N_RUNS: {N_RUNS}")
    print(f"    Model:  {MODEL_SIZE}")
    print(f"    Target: '{TARGET_WORD}'")
    
    ensure_output_dir()
    
    # Load model once
    model = load_model()
    
    # Files to analyze
    fullsentence_path = os.path.join(AUDIO_STIMULI_DIR, "fullsentence.wav")
    
    # Check files exist
    if not os.path.exists(fullsentence_path):
        print(f"ERROR: Could not find {fullsentence_path}")
        return
    
    # Run alignments on fullsentence
    print(f"\n{'-'*70}")
    print(f"  Analyzing: fullsentence.wav ({N_RUNS} runs)")
    print(f"{'-'*70}")
    
    all_runs_fullsentence = run_multiple_alignments(model, fullsentence_path, N_RUNS, "fullsentence")
    
    stats_fullsentence = calculate_statistics(all_runs_fullsentence)
    print_statistics(stats_fullsentence, "FULLSENTENCE.WAV - WITHIN-METHOD CONSISTENCY")
    
    # Save summary
    summary = {
        "tool": "whisper",
        "model": MODEL_SIZE,
        "n_runs": N_RUNS,
        "audio_file": "fullsentence.wav",
        "statistics": stats_fullsentence,
        "all_runs": all_runs_fullsentence
    }
    save_results(summary, os.path.join(OUTPUT_DIR, "fullsentence_summary.json"))
    
    print(f"\n{'='*70}")
    print(f"  WHISPER ALIGNMENT COMPLETE")
    print(f"  Results saved to: {OUTPUT_DIR}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
