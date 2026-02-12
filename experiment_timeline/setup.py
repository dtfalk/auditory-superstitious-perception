"""
Setup Subtimeline
=================
Handles initialization of pygame, audio device selection, and window creation.
"""

import os
import sys
import argparse
import pygame as pg
import sounddevice as sd

# Import from experiment_helpers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.audioEngine import AudioEngine


def pick_output_device(
    prefer_substrings: tuple[str, ...] = ("Speakers", "Realtek"),
    exclude_substrings: tuple[str, ...] = (),
    skip_default: bool = False,
) -> tuple[int, str]:
    """
    Select the best audio output device.
    
    Args:
        prefer_substrings: Preferred device name substrings
        exclude_substrings: Device name substrings to exclude
        skip_default: Skip the system default device
        
    Returns:
        Tuple of (device index, device name)
    """
    devs = sd.query_devices()
    hostapis = sd.query_hostapis()
    wasapi_ids = [i for i, api in enumerate(hostapis) if "WASAPI" in api["name"].upper()]
    wasapi_id = wasapi_ids[0] if wasapi_ids else None

    def _name_ok(name: str) -> bool:
        lname = name.lower()
        for bad in exclude_substrings:
            if bad and bad.lower() in lname:
                return False
        return True

    # 1) Try PortAudio default output first
    if not skip_default:
        default_out = sd.default.device[1]
        if default_out is not None and default_out >= 0:
            d = devs[default_out]
            if d["max_output_channels"] > 0 and _name_ok(d["name"]):
                return default_out, d["name"]

    # 2) Prefer common speaker strings on WASAPI devices
    if wasapi_id is not None:
        candidates = [
            (i, d["name"]) for i, d in enumerate(devs)
            if d["max_output_channels"] > 0 and d["hostapi"] == wasapi_id and _name_ok(d["name"])
        ]
        for substr in prefer_substrings:
            for i, name in candidates:
                if substr.lower() in name.lower():
                    return i, name
        if candidates:
            return candidates[0]

    # 3) Final fallback: first output device
    for i, d in enumerate(devs):
        if d["max_output_channels"] > 0 and _name_ok(d["name"]):
            return i, d["name"]

    raise RuntimeError("No output devices found")


def set_high_priority() -> None:
    """Set the process to high priority on Windows for better audio performance."""
    if sys.platform != "win32":
        return
    try:
        import psutil
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS)
    except Exception as e:
        print("Could not set HIGH priority:", e)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--audio-device",
        type=int,
        default=None,
        help="Force a specific sounddevice output device index (overrides all auto-selection).",
    )
    parser.add_argument(
        "--dev-speakers",
        action="store_true",
        help="Dev mode: bypass system default (often HDMI) and prefer built-in laptop speakers.",
    )
    return parser.parse_args()


def run_setup(
    args: argparse.Namespace | None = None,
    win_width: int | None = None,
    win_height: int | None = None,
) -> tuple[pg.Surface, AudioEngine]:
    """
    Initialize pygame, audio device, and create the experiment window.
    
    Args:
        args: Parsed command line arguments (if None, will parse)
        win_width: Window width (if None, uses experimenterLevers.WIN_WIDTH)
        win_height: Window height (if None, uses experimenterLevers.WIN_HEIGHT)
        
    Returns:
        Tuple of (pygame window surface, AudioEngine instance)
    """
    if args is None:
        args = parse_args()
    
    # Import screen dimensions from experimenterLevers
    if win_width is None or win_height is None:
        # Use relative import path
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'experiment_helpers'))
        from experimenterLevers import WIN_WIDTH, WIN_HEIGHT
        win_width = win_width or WIN_WIDTH
        win_height = win_height or WIN_HEIGHT
    
    # Set high priority for better audio performance
    set_high_priority()
    
    # Initialize pygame
    pg.init()
    
    # Select audio device
    env_dev = os.getenv("ASP_DEV_SPEAKERS", "").strip().lower() in {"1", "true", "yes", "on"}
    dev_speakers = bool(args.dev_speakers or env_dev)

    if args.audio_device is not None:
        audio_device = int(args.audio_device)
        dev_name = sd.query_devices(audio_device)["name"]
    elif dev_speakers:
        audio_device, dev_name = pick_output_device(
            prefer_substrings=("Speakers", "Realtek", "Internal"),
            exclude_substrings=("HDMI", "NVIDIA", "Intel", "Display", "Monitor"),
            skip_default=True,
        )
    else:
        audio_device, dev_name = pick_output_device()

    print("Using output:", audio_device, dev_name)

    # Create audio engine
    audio_engine = AudioEngine(device_index=audio_device, samplerate=44100, blocksize=256)

    # Create fullscreen window
    win = pg.display.set_mode((win_width, win_height), pg.FULLSCREEN)
    pg.mouse.set_visible(False)
    
    return win, audio_engine
