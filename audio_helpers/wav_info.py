import sys
import os
import soundfile as sf

print("wav_info.py started")

if len(sys.argv) < 2:
    print("No path provided")
    sys.exit(1)

path = sys.argv[1]
print("Path argument:", path)

if not os.path.exists(path):
    print("Path does not exist")
    sys.exit(1)

if not path.lower().endswith(".wav"):
    print("Not a wav file")
    sys.exit(1)

data, sr = sf.read(path)
info = sf.info(path)

duration = info.frames / sr

print("File:", path)
print("Sample rate:", sr)
print("Channels:", info.channels)
print("Frames:", info.frames)
print("Duration (s):", round(duration, 3))
print("Subtype:", info.subtype)
print("Format:", info.format)
print("DONE")
