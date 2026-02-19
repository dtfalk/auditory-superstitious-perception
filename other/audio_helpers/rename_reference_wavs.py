#!/usr/bin/env python3
"""Rename reference WAV files to remove the _{number} suffix."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

for folder in PROJECT_ROOT.glob("audio_stimuli_*"):
    if not folder.is_dir():
        continue
    
    # Extract the number from folder name
    try:
        num = folder.name.split("_")[-1]
    except:
        continue
    
    renames = [
        (f"fullsentence_{num}.wav", "fullsentence.wav"),
        (f"wall_{num}.wav", "wall.wav"),
        (f"fullsentenceminuswall_{num}.wav", "fullsentenceminuswall.wav"),
    ]
    
    for old_name, new_name in renames:
        old_path = folder / old_name
        new_path = folder / new_name
        if old_path.exists():
            old_path.rename(new_path)
            print(f"Renamed: {old_path.name} -> {new_name} in {folder.name}")
        else:
            print(f"Not found: {old_path}")

print("\nDone.")
