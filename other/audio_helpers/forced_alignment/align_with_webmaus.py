"""
Forced Alignment using WebMAUS (BAS Web Services) - Multiple Runs Version

WebMAUS is the web service from the Bavarian Archive for Speech Signals (BAS).
It's an established tool in phonetics research with no local installation required.

=============================================================================
INSTALLATION
=============================================================================

No installation needed! WebMAUS is a REST API.

Just need the requests library (likely already installed):
    pip install requests

=============================================================================

Usage:
    python align_with_webmaus.py

Note: Requires internet connection. Audio is uploaded to BAS servers.
For sensitive data, consider using local tools (MFA, Gentle) instead.

Website: https://clarin.phonetik.uni-muenchen.de/BASWebServices/
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

# The transcript for fullsentence.wav
FULLSENTENCE_TRANSCRIPT = "The picture hung on the wall"

# The transcript for targetwall.wav
TARGETWALL_TRANSCRIPT = "wall"

# WebMAUS API endpoint
WEBMAUS_URL = "https://clarin.phonetik.uni-muenchen.de/BASWebServices/services/runMAUSBasic"

# =============================================================================
# PATHS
# =============================================================================

AUDIO_STIMULI_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "audio_stimuli")
OUTPUT_BASE_DIR = os.path.join(os.path.dirname(__file__), "results")
OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "webmaus")

# =============================================================================


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def align_with_webmaus_single(audio_path, transcript, run_number):
    """
    Send audio and transcript to WebMAUS for alignment.
    
    WebMAUS returns a Praat TextGrid which we parse for word timings.
    """
    print(f"  Run {run_number}: Aligning {os.path.basename(audio_path)}...", end=" ", flush=True)
    
    start_time = time.time()
    
    # Prepare the request
    with open(audio_path, 'rb') as audio_file:
        files = {
            'SIGNAL': (os.path.basename(audio_path), audio_file, 'audio/wav'),
        }
        data = {
            'TEXT': transcript,
            'LANGUAGE': 'eng-US',  # American English
            'OUTFORMAT': 'json',   # Get JSON output instead of TextGrid
        }
        
        try:
            response = requests.post(
                WEBMAUS_URL,
                files=files,
                data=data,
                timeout=60  # WebMAUS can be slow
            )
        except requests.exceptions.Timeout:
            print("TIMEOUT")
            return None
        except requests.exceptions.ConnectionError:
            print("CONNECTION ERROR")
            return None
    
    elapsed = time.time() - start_time
    
    if response.status_code != 200:
        print(f"ERROR {response.status_code}")
        return None
    
    # Parse the response
    try:
        result = response.json()
        print(f"done ({elapsed:.2f}s)")
        return result
    except json.JSONDecodeError:
        # WebMAUS might return TextGrid even when JSON requested
        # Try to parse as TextGrid
        print(f"done ({elapsed:.2f}s) [parsing TextGrid]")
        return parse_textgrid_response(response.text)


def parse_textgrid_response(textgrid_text):
    """Parse TextGrid response from WebMAUS."""
    import re
    
    words = []
    
    # Find ORT (orthography/words) tier
    ort_match = re.search(
        r'name\s*=\s*"ORT".*?intervals:\s*size\s*=\s*(\d+)(.*?)(?=item\s*\[|$)',
        textgrid_text,
        re.IGNORECASE | re.DOTALL
    )
    
    if ort_match:
        intervals_text = ort_match.group(2)
        
        # Find all intervals
        interval_pattern = r'intervals\s*\[\d+\].*?xmin\s*=\s*([\d.]+).*?xmax\s*=\s*([\d.]+).*?text\s*=\s*"([^"]*)"'
        
        for match in re.finditer(interval_pattern, intervals_text, re.DOTALL):
            xmin, xmax, text = match.groups()
            xmin, xmax = float(xmin), float(xmax)
            
            if text.strip() and text.strip() != "<p:>":  # Skip pauses
                words.append({
                    "word": text.strip(),
                    "start": xmin,
                    "end": xmax,
                    "duration": xmax - xmin
                })
    
    return {"words": words, "format": "textgrid"}


def extract_word_timings(result):
    """Extract word timings from WebMAUS result."""
    if not result:
        return []
    
    # If already parsed from TextGrid
    if "words" in result:
        return result["words"]
    
    # Parse JSON format from WebMAUS
    words = []
    
    # WebMAUS JSON format
    if "mpiAnnotation" in result:
        for tier in result.get("mpiAnnotation", {}).get("tiers", []):
            if tier.get("tierId") == "ORT":  # Orthography tier = words
                for item in tier.get("items", []):
                    if item.get("value") and item.get("value") != "<p:>":
                        start = float(item.get("begin", 0)) / 1000  # ms to seconds
                        end = float(item.get("end", 0)) / 1000
                        words.append({
                            "word": item["value"],
                            "start": start,
                            "end": end,
                            "duration": end - start
                        })
    
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


def run_multiple_alignments(audio_path, transcript, n_runs, audio_name):
    """Run alignment n_runs times and collect results."""
    all_runs = []
    
    for run_idx in range(n_runs):
        result = align_with_webmaus_single(audio_path, transcript, run_idx + 1)
        words = extract_word_timings(result) if result else []
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
        
        # Small delay between requests to be nice to the server
        if run_idx < n_runs - 1:
            time.sleep(1)
    
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
    print("  WEBMAUS (BAS) FORCED ALIGNMENT - MULTIPLE RUNS")
    print("="*70)
    print(f"\n  Configuration:")
    print(f"    N_RUNS: {N_RUNS}")
    print(f"    Target: '{TARGET_WORD}'")
    print(f"\n  Note: Audio is uploaded to BAS servers (Germany).")
    print(f"  For sensitive data, use local tools instead.")
    
    ensure_output_dir()
    
    # Files to analyze
    fullsentence_path = os.path.join(AUDIO_STIMULI_DIR, "fullsentence.wav")
    targetwall_path = os.path.join(AUDIO_STIMULI_DIR, "targetwall.wav")
    
    # Check files exist
    if not os.path.exists(fullsentence_path):
        print(f"ERROR: Could not find {fullsentence_path}")
        return
    
    # Check internet connectivity
    print("\n  Checking connection to WebMAUS...")
    try:
        requests.get("https://clarin.phonetik.uni-muenchen.de/", timeout=10)
        print("  Connected!")
    except:
        print("  ERROR: Cannot reach WebMAUS servers. Check internet connection.")
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
        "tool": "webmaus",
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
        print(f"  Transcript: \"{TARGETWALL_TRANSCRIPT}\"")
        print(f"{'-'*70}")
        
        all_runs_targetwall = run_multiple_alignments(
            targetwall_path, TARGETWALL_TRANSCRIPT, N_RUNS, "targetwall"
        )
        
        stats_targetwall = calculate_statistics(all_runs_targetwall)
        print_statistics(stats_targetwall, "TARGETWALL.WAV - WITHIN-METHOD CONSISTENCY")
        
        summary_target = {
            "tool": "webmaus",
            "n_runs": N_RUNS,
            "audio_file": "targetwall.wav",
            "transcript": TARGETWALL_TRANSCRIPT,
            "statistics": stats_targetwall,
            "all_runs": all_runs_targetwall
        }
        save_results(summary_target, os.path.join(OUTPUT_DIR, "targetwall_summary.json"))
    
    print(f"\n{'='*70}")
    print(f"  WEBMAUS ALIGNMENT COMPLETE")
    print(f"  Results saved to: {OUTPUT_DIR}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
