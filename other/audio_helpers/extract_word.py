"""
Extract a target word from a WAV file using MFA-determined boundaries.

Usage:
    python extract_word.py                          # Uses defaults below
    python extract_word.py <input.wav> <output.wav> <start_s> <end_s>

The default boundaries come from the MFA forced alignment analysis of
fullsentence.wav, which placed "wall" at 1.180s – 1.630s.
"""

import sys
from pathlib import Path
import soundfile as sf


# =============================================================================
# DEFAULTS — MFA boundaries for "wall" in fullsentence.wav
# =============================================================================
AUDIO_STIMULI_DIR = Path(__file__).resolve().parent.parent.parent / "audio_stimuli"

DEFAULT_INPUT = AUDIO_STIMULI_DIR / "fullsentence.wav"
DEFAULT_OUTPUT = AUDIO_STIMULI_DIR / "wall.wav"

# MFA alignment result (seconds)
DEFAULT_START_S = 1.180
DEFAULT_END_S = 1.630


def extract_segment(input_path: Path, output_path: Path, start_s: float, end_s: float):
    """Extract a time segment from a WAV file and save it."""
    data, sr = sf.read(input_path, always_2d=False)
    info = sf.info(input_path)

    start_sample = int(round(start_s * sr))
    end_sample = int(round(end_s * sr))

    # Clamp to valid range
    start_sample = max(0, start_sample)
    end_sample = min(len(data), end_sample)

    segment = data[start_sample:end_sample]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), segment, sr, subtype=info.subtype, format=info.format)

    duration_ms = (end_sample - start_sample) / sr * 1000
    print(f"Extracted '{output_path.name}'")
    print(f"  Source:     {input_path}")
    print(f"  Boundaries: {start_s:.3f}s – {end_s:.3f}s  ({duration_ms:.1f} ms)")
    print(f"  Samples:    {start_sample} – {end_sample}  (sr={sr})")
    print(f"  Saved to:   {output_path}")


def main():
    if len(sys.argv) == 5:
        input_path = Path(sys.argv[1]).resolve()
        output_path = Path(sys.argv[2]).resolve()
        start_s = float(sys.argv[3])
        end_s = float(sys.argv[4])
    elif len(sys.argv) == 1:
        input_path = DEFAULT_INPUT
        output_path = DEFAULT_OUTPUT
        start_s = DEFAULT_START_S
        end_s = DEFAULT_END_S
    else:
        print("Usage:")
        print("  python extract_word.py")
        print("  python extract_word.py <input.wav> <output.wav> <start_s> <end_s>")
        sys.exit(1)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    extract_segment(input_path, output_path, start_s, end_s)


if __name__ == "__main__":
    main()
