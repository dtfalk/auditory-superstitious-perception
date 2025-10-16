import os
import sys
import librosa
import soundfile as sf
import numpy as np

def rms_db(signal):
    """Compute RMS level in dBFS."""
    rms = np.sqrt(np.mean(signal ** 2))
    return 20 * np.log10(rms + 1e-10)  # avoid log(0)

def normalize_file(file_path, ref_db):
    """Normalize a single WAV file in place to match reference dB."""
    audio, sr = librosa.load(file_path, sr=None, mono=True)
    tgt_db = rms_db(audio)
    diff_db = ref_db - tgt_db

    gain = 10 ** (diff_db / 20)
    adjusted = audio * gain

    # Prevent clipping
    max_val = np.max(np.abs(adjusted))
    if max_val > 1.0:
        print(f"⚠️  {os.path.basename(file_path)}: clipping detected — normalizing down.")
        adjusted /= max_val

    sf.write(file_path, adjusted, sr)
    print(f"✔ {os.path.basename(file_path)}: {tgt_db:.2f} → {rms_db(adjusted):.2f} dBFS (gain {diff_db:+.2f} dB)")

def normalize_folder(folder_path, ref_db):
    """Normalize all WAV files in a folder in place."""
    if not os.path.isdir(folder_path):
        print(f"⚠️  Skipping '{folder_path}' (not a folder)")
        return

    print(f"\n📁 Normalizing folder: {folder_path}")
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".wav"):
            file_path = os.path.join(folder_path, filename)
            normalize_file(file_path, ref_db)

def main():
    if len(sys.argv) < 3:
        print("Usage: python normalize_inplace_flex.py reference.wav [folder_or_file1] [folder_or_file2] ...")
        sys.exit(1)

    ref_path = sys.argv[1]
    targets = sys.argv[2:]

    # Load reference and compute loudness
    ref, _ = librosa.load(ref_path, sr=None, mono=True)
    ref_db = rms_db(ref)
    print(f"Reference loudness: {ref_db:.2f} dBFS")

    # Process each target (folder or file)
    for target in targets:
        if os.path.isdir(target):
            normalize_folder(target, ref_db)
        elif target.lower().endswith(".wav") and os.path.isfile(target):
            normalize_file(target, ref_db)
        else:
            print(f"⚠️  Skipping '{target}' (not a valid WAV or folder)")

    print("\n✅ Normalization complete for all provided inputs.")

if __name__ == "__main__":
    main()
