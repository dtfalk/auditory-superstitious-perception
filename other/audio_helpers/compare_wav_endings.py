"""
Compare fullsentence.wav and targetwall.wav to see if the endings align in content.
Works backwards from the end of each file to check if the audio data matches.
"""

import os
import wave
import sys
import struct
import numpy as np

AUDIO_STIMULI_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "audio_stimuli")


def read_wav_samples(filepath):
    """Read WAV file and return samples as numpy array along with sample rate."""
    with wave.open(filepath, 'rb') as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        frame_rate = wf.getframerate()
        n_frames = wf.getnframes()
        
        raw_data = wf.readframes(n_frames)
        
        # Convert to numpy array based on sample width
        if sample_width == 1:
            samples = np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32) - 128
        elif sample_width == 2:
            samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)
        elif sample_width == 4:
            samples = np.frombuffer(raw_data, dtype=np.int32).astype(np.float32)
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")
        
        # If stereo, convert to mono by averaging channels
        if n_channels == 2:
            samples = samples.reshape(-1, 2).mean(axis=1)
        
        return samples, frame_rate


def compare_endings(file1, file2, compare_ms=100):
    """
    Compare the last N milliseconds of two audio files.
    Returns correlation coefficient and detailed comparison.
    """
    samples1, sr1 = read_wav_samples(file1)
    samples2, sr2 = read_wav_samples(file2)
    
    name1 = os.path.basename(file1)
    name2 = os.path.basename(file2)
    
    print("=" * 70)
    print(f"AUDIO CONTENT COMPARISON - Last {compare_ms}ms")
    print("=" * 70)
    
    print(f"\n{name1}:")
    print(f"  Total samples: {len(samples1):,}")
    print(f"  Duration: {len(samples1)/sr1*1000:.1f} ms")
    print(f"  Sample rate: {sr1} Hz")
    
    print(f"\n{name2}:")
    print(f"  Total samples: {len(samples2):,}")
    print(f"  Duration: {len(samples2)/sr2*1000:.1f} ms")
    print(f"  Sample rate: {sr2} Hz")
    
    if sr1 != sr2:
        print(f"\nERROR: Sample rates don't match ({sr1} vs {sr2})")
        return
    
    # Calculate how many samples for the comparison window
    compare_samples = int(sr1 * compare_ms / 1000)
    
    # Get the last N samples from each file
    end1 = samples1[-compare_samples:]
    end2 = samples2[-compare_samples:]
    
    # Make sure we have enough samples
    actual_compare = min(len(end1), len(end2))
    end1 = end1[-actual_compare:]
    end2 = end2[-actual_compare:]
    
    print(f"\nComparing last {actual_compare} samples ({actual_compare/sr1*1000:.1f} ms)")
    
    # Compute correlation
    correlation = np.corrcoef(end1, end2)[0, 1]
    
    # Compute mean absolute difference
    mae = np.mean(np.abs(end1 - end2))
    
    # Compute if samples are identical
    exact_match = np.array_equal(end1, end2)
    
    # Compute max difference
    max_diff = np.max(np.abs(end1 - end2))
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    print(f"\n  Correlation coefficient: {correlation:.6f}")
    print(f"  Mean absolute difference: {mae:.2f}")
    print(f"  Max absolute difference: {max_diff:.2f}")
    print(f"  Exact match: {'YES' if exact_match else 'NO'}")
    
    if correlation > 0.99:
        print("\n  VERDICT: The endings are virtually IDENTICAL")
    elif correlation > 0.9:
        print("\n  VERDICT: The endings are VERY SIMILAR (minor differences)")
    elif correlation > 0.7:
        print("\n  VERDICT: The endings are SOMEWHAT SIMILAR")
    elif correlation > 0.3:
        print("\n  VERDICT: The endings have LOW similarity")
    else:
        print("\n  VERDICT: The endings DO NOT MATCH")
    
    # Also try cross-correlation to find best alignment offset
    print("\n" + "-" * 70)
    print("ALIGNMENT CHECK")
    print("-" * 70)
    
    # Use a larger window for cross-correlation check
    check_window = min(len(samples1), len(samples2), int(sr1 * 0.5))  # Up to 500ms
    
    end1_full = samples1[-check_window:]
    end2_full = samples2[-check_window:]
    
    # Normalize for cross-correlation
    end1_norm = (end1_full - np.mean(end1_full)) / (np.std(end1_full) + 1e-10)
    end2_norm = (end2_full - np.mean(end2_full)) / (np.std(end2_full) + 1e-10)
    
    # Cross-correlate to find best offset
    cross_corr = np.correlate(end1_norm, end2_norm, mode='full')
    best_offset_idx = np.argmax(cross_corr)
    best_offset = best_offset_idx - (len(end2_norm) - 1)
    
    print(f"\n  Best alignment offset: {best_offset} samples ({best_offset/sr1*1000:.2f} ms)")
    
    if abs(best_offset) < 5:
        print("  The files appear to be perfectly aligned at the end.")
    elif best_offset > 0:
        print(f"  {name2} appears to end {abs(best_offset/sr1*1000):.2f} ms BEFORE {name1}")
    else:
        print(f"  {name1} appears to end {abs(best_offset/sr1*1000):.2f} ms BEFORE {name2}")
    
    print("\n" + "=" * 70)
    
    return correlation, mae, exact_match


def find_target_in_source(source_file, target_file, search_last_ms=1000):
    """
    Use sliding window cross-correlation to find where target audio
    best matches within the source audio.
    
    Searches the last search_last_ms of the source file.
    """
    source_samples, sr1 = read_wav_samples(source_file)
    target_samples, sr2 = read_wav_samples(target_file)
    
    source_name = os.path.basename(source_file)
    target_name = os.path.basename(target_file)
    
    print("\n" + "=" * 70)
    print(f"SLIDING WINDOW SEARCH")
    print(f"Finding '{target_name}' within '{source_name}'")
    print("=" * 70)
    
    if sr1 != sr2:
        print(f"\nERROR: Sample rates don't match ({sr1} vs {sr2})")
        return
    
    # Get the region to search (last N ms of source)
    search_samples = int(sr1 * search_last_ms / 1000)
    search_region = source_samples[-search_samples:]
    
    print(f"\n  Searching last {search_last_ms} ms of {source_name}")
    print(f"  Looking for {len(target_samples)} samples ({len(target_samples)/sr1*1000:.1f} ms) of {target_name}")
    
    # Normalize target for correlation
    target_norm = (target_samples - np.mean(target_samples)) / (np.std(target_samples) + 1e-10)
    
    # Sliding window correlation
    window_size = len(target_samples)
    n_windows = len(search_region) - window_size + 1
    
    if n_windows <= 0:
        print(f"\n  ERROR: Target is longer than search region")
        return
    
    correlations = []
    for i in range(n_windows):
        window = search_region[i:i + window_size]
        window_norm = (window - np.mean(window)) / (np.std(window) + 1e-10)
        corr = np.corrcoef(window_norm, target_norm)[0, 1]
        correlations.append(corr)
    
    correlations = np.array(correlations)
    best_idx = np.argmax(correlations)
    best_corr = correlations[best_idx]
    
    # Calculate position from end of file
    position_from_search_start = best_idx
    position_from_source_end = len(search_region) - best_idx - window_size
    
    # Time calculations
    time_from_source_end_ms = position_from_source_end / sr1 * 1000
    absolute_position_ms = (len(source_samples) - search_samples + best_idx) / sr1 * 1000
    
    print("\n" + "-" * 70)
    print("BEST MATCH FOUND")
    print("-" * 70)
    
    print(f"\n  Best correlation: {best_corr:.4f}")
    print(f"\n  Match location in {source_name}:")
    print(f"    Starts at: {absolute_position_ms:.1f} ms from beginning")
    print(f"    Ends at:   {absolute_position_ms + len(target_samples)/sr1*1000:.1f} ms from beginning")
    print(f"    Gap from end of {source_name}: {time_from_source_end_ms:.1f} ms")
    
    if best_corr > 0.9:
        print(f"\n  VERDICT: STRONG MATCH - '{target_name}' found in '{source_name}'")
        if time_from_source_end_ms < 10:
            print(f"           The files align at the end!")
        else:
            print(f"           BUT there's {time_from_source_end_ms:.1f} ms of audio AFTER the match in {source_name}")
    elif best_corr > 0.7:
        print(f"\n  VERDICT: MODERATE MATCH - Likely the same content with some differences")
    elif best_corr > 0.5:
        print(f"\n  VERDICT: WEAK MATCH - Possibly related content")
    else:
        print(f"\n  VERDICT: NO MATCH - Content does not appear to be present")
    
    # Also show top 5 match positions
    print("\n" + "-" * 70)
    print("TOP 5 MATCH POSITIONS")
    print("-" * 70)
    
    top_indices = np.argsort(correlations)[-5:][::-1]
    for rank, idx in enumerate(top_indices, 1):
        pos_ms = (len(source_samples) - search_samples + idx) / sr1 * 1000
        gap_ms = (len(search_region) - idx - window_size) / sr1 * 1000
        print(f"  {rank}. Correlation: {correlations[idx]:.4f} at {pos_ms:.1f} ms (gap from end: {gap_ms:.1f} ms)")
    
    print("\n" + "=" * 70)
    
    return best_corr, absolute_position_ms, time_from_source_end_ms


def analyze_and_extract_trailing(source_file, trailing_ms, output_file=None):
    """
    Analyze the trailing portion of an audio file and optionally extract it.
    """
    samples, sr = read_wav_samples(source_file)
    source_name = os.path.basename(source_file)
    
    trailing_samples = int(sr * trailing_ms / 1000)
    trailing_audio = samples[-trailing_samples:]
    
    print("\n" + "=" * 70)
    print(f"TRAILING AUDIO ANALYSIS - Last {trailing_ms:.1f} ms of {source_name}")
    print("=" * 70)
    
    # Basic statistics
    rms = np.sqrt(np.mean(trailing_audio ** 2))
    peak = np.max(np.abs(trailing_audio))
    mean_abs = np.mean(np.abs(trailing_audio))
    
    # Compare to overall file RMS
    overall_rms = np.sqrt(np.mean(samples ** 2))
    
    # Check for silence (very low RMS compared to file)
    silence_threshold = overall_rms * 0.1  # 10% of overall RMS
    
    print(f"\n  Trailing audio statistics:")
    print(f"    Duration: {trailing_ms:.1f} ms ({trailing_samples} samples)")
    print(f"    RMS level: {rms:.2f}")
    print(f"    Peak level: {peak:.2f}")
    print(f"    Mean absolute: {mean_abs:.2f}")
    print(f"\n  Overall file RMS: {overall_rms:.2f}")
    print(f"  Trailing/Overall RMS ratio: {rms/overall_rms:.2%}")
    
    if rms < silence_threshold:
        print(f"\n  VERDICT: Trailing audio is essentially SILENCE (< 10% of file RMS)")
    elif rms < overall_rms * 0.3:
        print(f"\n  VERDICT: Trailing audio is QUIET (background noise/room tone)")
    else:
        print(f"\n  VERDICT: Trailing audio contains SIGNIFICANT CONTENT")
    
    # Zero crossing rate (indicator of speech vs silence)
    zero_crossings = np.sum(np.abs(np.diff(np.sign(trailing_audio))) > 0)
    zcr = zero_crossings / len(trailing_audio)
    print(f"\n  Zero crossing rate: {zcr:.4f}")
    if zcr > 0.1:
        print(f"    (High ZCR suggests speech/fricative content)")
    elif zcr > 0.02:
        print(f"    (Moderate ZCR suggests voiced content or noise)")
    else:
        print(f"    (Low ZCR suggests near-silence or low-frequency hum)")
    
    # Extract to file if requested
    if output_file:
        # Need to write as WAV
        with wave.open(source_file, 'rb') as wf:
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            frame_rate = wf.getframerate()
        
        # Convert back to int16
        trailing_int16 = trailing_audio.astype(np.int16)
        
        with wave.open(output_file, 'wb') as wf:
            wf.setnchannels(1)  # Mono (we converted to mono in read)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(frame_rate)
            wf.writeframes(trailing_int16.tobytes())
        
        print(f"\n  Extracted to: {output_file}")
        print(f"  File size: {os.path.getsize(output_file):,} bytes")
    
    print("\n" + "=" * 70)
    
    return rms, peak, rms/overall_rms


if __name__ == "__main__":
    fullsentence_path = os.path.join(AUDIO_STIMULI_DIR, "fullsentence.wav")
    targetwall_path = os.path.join(AUDIO_STIMULI_DIR, "targetwall.wav")
    
    # Check files exist
    if not os.path.exists(fullsentence_path):
        print(f"ERROR: Could not find {fullsentence_path}")
        sys.exit(1)
    if not os.path.exists(targetwall_path):
        print(f"ERROR: Could not find {targetwall_path}")
        sys.exit(1)
    
    # First do the simple end comparison
    compare_endings(fullsentence_path, targetwall_path, compare_ms=100)
    
    # Then do sliding window search
    result = find_target_in_source(fullsentence_path, targetwall_path, search_last_ms=1000)
    
    # Analyze and extract trailing audio
    if result:
        _, _, trailing_ms = result
        trailing_output = os.path.join(AUDIO_STIMULI_DIR, "trailing_audio_extracted.wav")
        analyze_and_extract_trailing(fullsentence_path, trailing_ms, trailing_output)
