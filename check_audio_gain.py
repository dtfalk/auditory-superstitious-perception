#!/usr/bin/env python3
"""
Check Audio Gain Levels
=======================
Crawls the audio_stimuli folder and reports the RMS level of each WAV file
to verify all audio files are normalized to the same level.

Usage:
    python check_audio_gain.py
"""

import os
import wave
import numpy as np
from pathlib import Path


def get_rms_db(filepath: str) -> tuple[float, float, int]:
    """
    Calculate RMS level in dB for a WAV file.
    
    Returns:
        (rms_db, peak_db, sample_rate)
    """
    with wave.open(filepath, 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        
        raw_data = wf.readframes(n_frames)
    
    # Convert to numpy array
    if sampwidth == 1:
        dtype = np.uint8
        max_val = 128.0
    elif sampwidth == 2:
        dtype = np.int16
        max_val = 32768.0
    elif sampwidth == 4:
        dtype = np.int32
        max_val = 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")
    
    samples = np.frombuffer(raw_data, dtype=dtype).astype(np.float64)
    
    # Convert to mono if stereo
    if n_channels == 2:
        samples = samples.reshape(-1, 2).mean(axis=1)
    
    # Normalize to -1 to 1 range
    samples = samples / max_val
    
    # Calculate RMS
    rms = np.sqrt(np.mean(samples ** 2))
    rms_db = 20 * np.log10(rms) if rms > 0 else -np.inf
    
    # Calculate peak
    peak = np.max(np.abs(samples))
    peak_db = 20 * np.log10(peak) if peak > 0 else -np.inf
    
    return rms_db, peak_db, sample_rate


def main():
    script_dir = Path(__file__).parent
    audio_dir = script_dir / 'audio_stimuli'
    
    if not audio_dir.exists():
        print(f"Error: audio_stimuli folder not found at {audio_dir}")
        return 1
    
    # Find all WAV files
    wav_files = list(audio_dir.rglob('*.wav'))
    
    if not wav_files:
        print("No WAV files found in audio_stimuli folder")
        return 1
    
    print(f"Found {len(wav_files)} WAV files\n")
    print(f"{'File':<60} {'RMS (dB)':<12} {'Peak (dB)':<12} {'Sample Rate':<12}")
    print("-" * 96)
    
    rms_values = []
    results = []
    
    for wav_path in sorted(wav_files):
        try:
            rms_db, peak_db, sample_rate = get_rms_db(str(wav_path))
            rel_path = wav_path.relative_to(audio_dir)
            results.append((str(rel_path), rms_db, peak_db, sample_rate))
            if rms_db != -np.inf:
                rms_values.append(rms_db)
        except Exception as e:
            rel_path = wav_path.relative_to(audio_dir)
            print(f"{str(rel_path):<60} ERROR: {e}")
    
    # Print results
    for rel_path, rms_db, peak_db, sample_rate in results:
        rms_str = f"{rms_db:.2f}" if rms_db != -np.inf else "-inf"
        peak_str = f"{peak_db:.2f}" if peak_db != -np.inf else "-inf"
        print(f"{rel_path:<60} {rms_str:<12} {peak_str:<12} {sample_rate:<12}")
    
    # Summary
    if rms_values:
        print("\n" + "=" * 96)
        print("SUMMARY")
        print("=" * 96)
        
        min_rms = min(rms_values)
        max_rms = max(rms_values)
        mean_rms = np.mean(rms_values)
        std_rms = np.std(rms_values)
        
        print(f"RMS Range:    {min_rms:.2f} dB to {max_rms:.2f} dB (spread: {max_rms - min_rms:.2f} dB)")
        print(f"RMS Mean:     {mean_rms:.2f} dB")
        print(f"RMS Std Dev:  {std_rms:.2f} dB")
        
        # Check if levels are consistent (within 1 dB)
        tolerance = 1.0
        if max_rms - min_rms <= tolerance:
            print(f"\n✓ All files are within {tolerance} dB of each other - CONSISTENT")
        else:
            print(f"\n✗ Files vary by more than {tolerance} dB - INCONSISTENT")
            print("\nFiles outside ±0.5 dB of mean:")
            for rel_path, rms_db, _, _ in results:
                if rms_db != -np.inf and abs(rms_db - mean_rms) > 0.5:
                    diff = rms_db - mean_rms
                    print(f"  {rel_path}: {rms_db:.2f} dB ({diff:+.2f} dB from mean)")
    
    return 0


if __name__ == '__main__':
    exit(main())
