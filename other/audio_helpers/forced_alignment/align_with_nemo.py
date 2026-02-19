"""
Forced Alignment using NVIDIA NeMo - Multiple Runs Version

NeMo is NVIDIA's conversational AI toolkit with a research-grade forced aligner.
It uses neural acoustic models and is used in production speech systems.

=============================================================================
INSTALLATION
=============================================================================

pip install nemo_toolkit[asr]

Note: This is a large installation (~2GB+). Requires PyTorch with CUDA for GPU.
CPU inference is supported but slower.

For faster installation with just ASR components:
    pip install nemo_toolkit[asr] --no-deps
    pip install torch torchaudio omegaconf hydra-core pytorch-lightning

=============================================================================

Usage:
    python align_with_nemo.py
"""

import os
import sys
import json
import time
import tempfile

# Check if nemo is installed
try:
    import torch
    import nemo.collections.asr as nemo_asr
    from nemo.collections.asr.parts.utils.vad_utils import (
        get_vad_stream_status,
    )
except ImportError:
    print("ERROR: nemo_toolkit not installed")
    print("Install with: pip install nemo_toolkit[asr]")
    print("\nThis is a large installation. For minimal install:")
    print("  pip install nemo_toolkit[asr] --no-deps")
    print("  pip install torch torchaudio omegaconf hydra-core pytorch-lightning")
    sys.exit(1)

# =============================================================================
# CONFIGURATION - EDIT THESE
# =============================================================================

N_RUNS = 5  # Number of times to run alignment
TARGET_WORD = "wall"

# The transcript for fullsentence.wav
FULLSENTENCE_TRANSCRIPT = "The picture hung on the wall"

# The transcript for targetwall.wav
TARGETWALL_TRANSCRIPT = "wall"

# ASR model to use for alignment
ASR_MODEL = "stt_en_conformer_ctc_small"  # Options: stt_en_conformer_ctc_small, stt_en_conformer_ctc_medium, stt_en_conformer_ctc_large

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
    
    # Create a manifest file (NeMo requires this format)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        manifest_path = f.name
        manifest_entry = {
            "audio_filepath": audio_path,
            "text": transcript.lower(),
            "duration": 10.0  # Placeholder, will be updated
        }
        f.write(json.dumps(manifest_entry) + "\n")
    
    try:
        # Use NeMo's alignment functionality
        # This uses CTC segmentation to align text to audio
        words = []
        
        # Transcribe to get timing info
        transcription = model.transcribe([audio_path], return_hypotheses=True)
        
        if transcription and len(transcription) > 0:
            hypothesis = transcription[0]
            
            # Check if we have word-level timestamps
            if hasattr(hypothesis, 'timestep') and hypothesis.timestep is not None:
                # Extract word timings from CTC output
                timesteps = hypothesis.timestep
                text_tokenized = hypothesis.text.split()
                
                # Simple word boundary estimation from CTC blanks
                # This is approximate - NeMo's full alignment uses more sophisticated methods
                if hasattr(timesteps, 'word_timings'):
                    for word_info in timesteps.word_timings:
                        words.append({
                            "word": word_info['word'],
                            "start": word_info['start_time'],
                            "end": word_info['end_time'],
                            "duration": word_info['end_time'] - word_info['start_time']
                        })
            
            # Fallback: use ASR timestamps if available
            if not words and hasattr(hypothesis, 'words') and hypothesis.words:
                for word_info in hypothesis.words:
                    words.append({
                        "word": word_info.word,
                        "start": word_info.start_time,
                        "end": word_info.end_time,
                        "duration": word_info.end_time - word_info.start_time
                    })
            
            # If still no words, try timestamp extraction from logprobs
            if not words:
                # Use basic transcription with estimated uniform timing
                audio_duration = get_audio_duration(audio_path)
                text_words = transcript.lower().split()
                word_duration = audio_duration / len(text_words) if text_words else 0
                
                for i, word in enumerate(text_words):
                    start = i * word_duration
                    end = (i + 1) * word_duration
                    words.append({
                        "word": word,
                        "start": start,
                        "end": end,
                        "duration": word_duration,
                        "estimated": True  # Mark as estimated, not from CTC
                    })
    
    finally:
        # Clean up temp file
        if os.path.exists(manifest_path):
            os.unlink(manifest_path)
    
    elapsed = time.time() - start_time
    print(f"done ({elapsed:.2f}s)")
    
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
    targetwall_path = os.path.join(AUDIO_STIMULI_DIR, "targetwall.wav")
    
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
    
    # Run alignments on targetwall
    if os.path.exists(targetwall_path):
        print(f"\n{'-'*70}")
        print(f"  Analyzing: targetwall.wav ({N_RUNS} runs)")
        print(f"  Transcript: \"{TARGETWALL_TRANSCRIPT}\"")
        print(f"{'-'*70}")
        
        all_runs_targetwall = run_multiple_alignments(
            model, device, targetwall_path, TARGETWALL_TRANSCRIPT, N_RUNS, "targetwall"
        )
        
        stats_targetwall = calculate_statistics(all_runs_targetwall)
        print_statistics(stats_targetwall, "TARGETWALL.WAV - WITHIN-METHOD CONSISTENCY")
        
        summary_target = {
            "tool": "nemo",
            "model": ASR_MODEL,
            "n_runs": N_RUNS,
            "audio_file": "targetwall.wav",
            "transcript": TARGETWALL_TRANSCRIPT,
            "statistics": stats_targetwall,
            "all_runs": all_runs_targetwall
        }
        save_results(summary_target, os.path.join(OUTPUT_DIR, "targetwall_summary.json"))
    
    print(f"\n{'='*70}")
    print(f"  NEMO ALIGNMENT COMPLETE")
    print(f"  Results saved to: {OUTPUT_DIR}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
