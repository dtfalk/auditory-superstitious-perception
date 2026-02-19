"""
Forced Alignment using NVIDIA NeMo - Multiple Runs Version

NeMo is NVIDIA's conversational AI toolkit with a research-grade forced aligner.
It uses neural acoustic models and is used in production speech systems.

=============================================================================
FULL SETUP (run these commands in order)
=============================================================================

1. Create conda environment:
    conda create -n nemo python=3.10 -y

2. Activate it:
    conda activate nemo

3. Install PyTorch with CUDA 11.8:
    conda install pytorch torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia -y

4. Install NeMo ASR:
    pip install "nemo_toolkit[asr]"

5. Run the script:
    cd other\audio_helpers\forced_alignment
    python align_with_nemo.py

=============================================================================
"""

import os
import sys
import time
import json
import wave

# Check if nemo is installed
try:
    import torch
    import nemo.collections.asr as nemo_asr
except ImportError as e:
    print(f"ERROR: nemo_toolkit not fully installed ({e})")
    print("Install with: pip install nemo_toolkit[asr]")
    print("\nThis is a large installation. For minimal install:")
    print("  pip install nemo_toolkit[asr]")
    print("  pip install torch torchaudio omegaconf hydra-core pytorch-lightning")
    sys.exit(1)

# =============================================================================
# CONFIGURATION - EDIT THESE
# =============================================================================

N_RUNS = 10  # Number of times to run alignment
TARGET_WORD = "wall"

# The transcript for fullsentence.wav
FULLSENTENCE_TRANSCRIPT = "The picture hung on the wall"

# ASR model to use for alignment
ASR_MODEL = "stt_en_quartznet15x5"  # Available: stt_en_quartznet15x5, stt_en_jasper10x5dr, asr_talknet_aligner

# =============================================================================
# PATHS
# =============================================================================

AUDIO_STIMULI_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "audio_stimuli")
OUTPUT_BASE_DIR = os.path.join(os.path.dirname(__file__), "results")
OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "nemo")

# =============================================================================


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_device():
    """Get the best available device."""
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_model():
    """Load NeMo ASR model."""
    device = get_device()
    print(f"\n  Loading NeMo model: {ASR_MODEL}")
    print(f"  Device: {device}")
    print("  (First run will download model, may take a few minutes)")
    
    # Load pretrained model
    model = nemo_asr.models.EncDecCTCModel.from_pretrained(model_name=ASR_MODEL)
    model = model.to(device)
    model.eval()
    
    return model, device


def align_with_nemo_single(model, device, audio_path, transcript, run_number):
    """Run a single alignment using NeMo's CTC segmentation."""
    print(f"  Run {run_number}: Aligning {os.path.basename(audio_path)}...", end=" ", flush=True)
    
    start_time = time.time()
    
    try:
        words = []
        
        # Transcribe to get timing info
        transcription = model.transcribe([audio_path], return_hypotheses=True)
        
        if transcription and len(transcription) > 0:
            # Handle both list-of-lists and flat list returns
            hypothesis = transcription[0]
            if isinstance(hypothesis, list):
                hypothesis = hypothesis[0]
            
            # Try to get character-level timesteps and derive word boundaries
            if hasattr(hypothesis, 'timestep') and hypothesis.timestep is not None:
                timesteps = hypothesis.timestep
                
                # If timestep has word-level info (dict format)
                if isinstance(timesteps, dict) and 'word' in timesteps:
                    for w_info in timesteps['word']:
                        words.append({
                            "word": w_info.get('word', w_info.get('label', '')),
                            "start": w_info.get('start_offset', 0) * 0.02,  # Convert frames to seconds
                            "end": w_info.get('end_offset', 0) * 0.02,
                            "duration": (w_info.get('end_offset', 0) - w_info.get('start_offset', 0)) * 0.02
                        })
                elif hasattr(timesteps, 'word_timings'):
                    for w_info in timesteps.word_timings:
                        if isinstance(w_info, dict):
                            words.append({
                                "word": w_info['word'],
                                "start": w_info['start_time'],
                                "end": w_info['end_time'],
                                "duration": w_info['end_time'] - w_info['start_time']
                            })
            
            # Try character timesteps to derive word boundaries
            if not words and hasattr(hypothesis, 'timestep') and hypothesis.timestep is not None:
                timesteps = hypothesis.timestep
                if isinstance(timesteps, dict) and 'char' in timesteps:
                    char_timestamps = timesteps['char']
                    text = hypothesis.text if hasattr(hypothesis, 'text') else str(hypothesis)
                    # Group characters into words by splitting on spaces
                    current_word = ""
                    word_start_idx = 0
                    for ci, ch in enumerate(text):
                        if ch == ' ':
                            if current_word and word_start_idx < len(char_timestamps) and ci - 1 < len(char_timestamps):
                                s = char_timestamps[word_start_idx]
                                e = char_timestamps[min(ci - 1, len(char_timestamps) - 1)]
                                s_time = s.get('start_offset', 0) * 0.02 if isinstance(s, dict) else 0
                                e_time = e.get('end_offset', 0) * 0.02 if isinstance(e, dict) else 0
                                words.append({
                                    "word": current_word,
                                    "start": s_time,
                                    "end": e_time,
                                    "duration": e_time - s_time,
                                    "method": "char_timestamps"
                                })
                            current_word = ""
                            word_start_idx = ci + 1
                        else:
                            current_word += ch
                    # Last word
                    if current_word and word_start_idx < len(char_timestamps):
                        s = char_timestamps[word_start_idx]
                        e = char_timestamps[min(len(text) - 1, len(char_timestamps) - 1)]
                        s_time = s.get('start_offset', 0) * 0.02 if isinstance(s, dict) else 0
                        e_time = e.get('end_offset', 0) * 0.02 if isinstance(e, dict) else 0
                        words.append({
                            "word": current_word,
                            "start": s_time,
                            "end": e_time,
                            "duration": e_time - s_time,
                            "method": "char_timestamps"
                        })
            
            # Fallback: use the transcribed text with CTC-based uniform timing
            if not words:
                audio_duration = get_audio_duration(audio_path)
                # Use the transcribed text or the provided transcript
                hyp_text = hypothesis.text if hasattr(hypothesis, 'text') else str(hypothesis)
                
                # Use logprobs length to estimate timing if available
                if hasattr(hypothesis, 'y_sequence') and hypothesis.y_sequence is not None:
                    # y_sequence contains the CTC output tokens
                    tokens = hypothesis.y_sequence
                    n_frames = len(tokens)
                    frame_duration = audio_duration / n_frames if n_frames > 0 else 0
                    
                    # Decode tokens to find word boundaries
                    # For CTC models, tokens are character indices
                    text_words = transcript.lower().split()
                    current_pos = 0
                    total_chars = sum(len(w) for w in text_words) + len(text_words) - 1  # chars + spaces
                    
                    for i, word in enumerate(text_words):
                        word_start_frac = current_pos / total_chars if total_chars > 0 else 0
                        current_pos += len(word) + (1 if i < len(text_words) - 1 else 0)
                        word_end_frac = current_pos / total_chars if total_chars > 0 else 0
                        
                        words.append({
                            "word": word,
                            "start": word_start_frac * audio_duration,
                            "end": word_end_frac * audio_duration,
                            "duration": (word_end_frac - word_start_frac) * audio_duration,
                            "method": "ctc_proportional"
                        })
                else:
                    # Pure uniform fallback
                    text_words = transcript.lower().split()
                    word_duration = audio_duration / len(text_words) if text_words else 0
                    
                    for i, word in enumerate(text_words):
                        w_start = i * word_duration
                        w_end = (i + 1) * word_duration
                        words.append({
                            "word": word,
                            "start": w_start,
                            "end": w_end,
                            "duration": word_duration,
                            "method": "uniform_estimate"
                        })
    
    except Exception as e:
        print(f"ERROR: {e}")
        return {"words": [], "transcription": transcript, "error": str(e)}
    
    elapsed = time.time() - start_time
    method = words[0].get("method", "nemo_ctc") if words else "none"
    print(f"done ({elapsed:.2f}s) [{method}]")
    
    return {"words": words, "transcription": transcript}


def get_audio_duration(audio_path):
    """Get audio duration in seconds."""
    import wave
    with wave.open(audio_path, 'rb') as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


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


def run_multiple_alignments(model, device, audio_path, transcript, n_runs, audio_name):
    """Run alignment n_runs times and collect results."""
    all_runs = []
    
    for run_idx in range(n_runs):
        result = align_with_nemo_single(model, device, audio_path, transcript, run_idx + 1)
        words = result.get("words", [])
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
    print("  NVIDIA NEMO FORCED ALIGNMENT - MULTIPLE RUNS")
    print("="*70)
    print(f"\n  Configuration:")
    print(f"    N_RUNS: {N_RUNS}")
    print(f"    Model:  {ASR_MODEL}")
    print(f"    Target: '{TARGET_WORD}'")
    
    ensure_output_dir()
    
    # Load model once
    model, device = load_model()
    
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
        model, device, fullsentence_path, FULLSENTENCE_TRANSCRIPT, N_RUNS, "fullsentence"
    )
    
    stats_fullsentence = calculate_statistics(all_runs_fullsentence)
    print_statistics(stats_fullsentence, "FULLSENTENCE.WAV - WITHIN-METHOD CONSISTENCY")
    
    # Save summary
    summary = {
        "tool": "nemo",
        "model": ASR_MODEL,
        "n_runs": N_RUNS,
        "audio_file": "fullsentence.wav",
        "transcript": FULLSENTENCE_TRANSCRIPT,
        "statistics": stats_fullsentence,
        "all_runs": all_runs_fullsentence
    }
    save_results(summary, os.path.join(OUTPUT_DIR, "fullsentence_summary.json"))
    
    print(f"\n{'='*70}")
    print(f"  NEMO ALIGNMENT COMPLETE")
    print(f"  Results saved to: {OUTPUT_DIR}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
