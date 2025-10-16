import librosa
import soundfile as sf
import numpy as np
import sys

def rms_db(signal):
    """Return RMS in dBFS."""
    rms = np.sqrt(np.mean(signal ** 2))
    return 20 * np.log10(rms + 1e-10)  # add epsilon to avoid log(0)

def match_loudness(file_ref, file_target, out_file):
    # Load both audio files (librosa auto-normalizes to [-1, 1] float range)
    ref, sr_ref = librosa.load(file_ref, sr=None, mono=True)
    tgt, sr_tgt = librosa.load(file_target, sr=None, mono=True)

    # Ensure same sample rate
    if sr_ref != sr_tgt:
        print(f"Resampling target from {sr_tgt} Hz to {sr_ref} Hz...")
        tgt = librosa.resample(tgt, orig_sr=sr_tgt, target_sr=sr_ref)
        sr_tgt = sr_ref

    # Compute RMS in dB
    ref_db = rms_db(ref)
    tgt_db = rms_db(tgt)
    diff_db = ref_db - tgt_db

    print(f"Reference RMS: {ref_db:.2f} dBFS")
    print(f"Target RMS:    {tgt_db:.2f} dBFS")
    print(f"Applying gain: {diff_db:.2f} dB")

    # Apply uniform gain
    gain = 10 ** (diff_db / 20)
    tgt_matched = tgt * gain

    # Clip if any sample goes above 1.0 (prevent digital clipping)
    max_val = np.max(np.abs(tgt_matched))
    if max_val > 1.0:
        print("Warning: clipping detected — normalizing to avoid distortion.")
        tgt_matched /= max_val

    # Save the adjusted target
    sf.write(out_file, tgt_matched, sr_tgt)
    print(f"Saved equalized file to {out_file}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python match_loudness.py reference.wav target.wav output.wav")
        sys.exit(1)

    match_loudness(sys.argv[1], sys.argv[2], sys.argv[3])
