"""
Audio Engine Module
===================
Contains audio playback engine and audio processing utilities.
- AudioEngine: Real-time audio playback with mixing
- Audio loading, resampling, caching, and concatenation functions
"""

import os
import sys
import wave
import time
import atexit
import threading
import platform
import numpy as np
from scipy.signal import resample_poly
from sounddevice import query_devices, query_hostapis, WasapiSettings, OutputStream

# Ensure project root is on sys.path for experiment_helpers import
_AE_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AE_BASE_DIR not in sys.path:
    sys.path.insert(0, _AE_BASE_DIR)

from experiment_helpers.experimenterLevers import (
    FORCE_WASAPI_OR_ASIO_EXCLUSIVE,
    SHORT_STIMULUS_FADEIN_ENABLED,
    SHORT_STIMULUS_FADEIN_MS,
    SHORT_STIMULUS_FADEIN_MAX_STIM_MS,
    SHORT_STIMULUS_FADEOUT_ENABLED,
    SHORT_STIMULUS_FADEOUT_MS,
    SHORT_STIMULUS_FADEOUT_MAX_STIM_MS,
)

# =============================================================================
# AUDIO PROCESSING UTILITIES
# =============================================================================

def load_wav_mono_int16(path: str) -> tuple[np.ndarray, int]:
    """
    Load a WAV file and convert to mono int16.
    
    Args:
        path: Path to the WAV file
        
    Returns:
        Tuple of (audio data as int16 array, sample rate)
    """
    with wave.open(path, "rb") as wf:
        ch = wf.getnchannels()
        fs = wf.getframerate()
        sw = wf.getsampwidth()
        n = wf.getnframes()
        raw = wf.readframes(n)

    if sw != 2:
        raise ValueError(f"{path}: expected 16-bit PCM WAV, got sampwidth={sw}")

    x = np.frombuffer(raw, dtype=np.int16)
    if ch == 2:
        x = x.reshape(-1, 2).mean(axis=1).astype(np.int16)
    elif ch != 1:
        raise ValueError(f"{path}: expected mono or stereo, got {ch} channels")

    return x, fs


def resample_int16(x16: np.ndarray, fs_in: int, fs_out: int) -> np.ndarray:
    """
    Resample int16 audio data to a new sample rate.
    
    Args:
        x16: Audio data as int16 array
        fs_in: Input sample rate
        fs_out: Output sample rate
        
    Returns:
        Resampled audio data as int16 array
    """
    if fs_in == fs_out:
        return x16

    x = x16.astype(np.float32) / 32768.0
    g = np.gcd(fs_in, fs_out)
    y = resample_poly(x, fs_out // g, fs_in // g)
    y = np.clip(y, -1.0, 1.0)
    return (y * 32767.0).astype(np.int16)


# =============================================================================
# AUDIO CACHING
# =============================================================================

# Cached WAV loading (prevents disk I/O during trials)
_PCM_CACHE: dict[tuple[str, int], np.ndarray] = {}
_CONCAT_CACHE: dict[tuple[str, str, bool, int, int], np.ndarray] = {}


def get_pcm16_mono(path: str, fs_out: int) -> np.ndarray:
    """
    Load a WAV once, convert to mono int16, resample to fs_out, and cache.
    
    Args:
        path: Path to the WAV file
        fs_out: Target sample rate
        
    Returns:
        Cached PCM data as int16 array
    """
    key = (os.path.abspath(path), int(fs_out))
    pcm = _PCM_CACHE.get(key)
    if pcm is not None:
        return pcm

    x16, fs_in = load_wav_mono_int16(path)
    y16 = resample_int16(x16, fs_in, fs_out)
    _PCM_CACHE[key] = y16
    return y16


def preload_pcm16_mono(paths: list[str], fs_out: int) -> None:
    """
    Best-effort preload of multiple WAV paths into the cache.
    
    Args:
        paths: List of WAV file paths to preload
        fs_out: Target sample rate
    """
    for p in paths:
        if not p:
            continue
        if os.path.exists(p):
            get_pcm16_mono(p, fs_out)


def concatenate_wavs(
    prefix_path: str, 
    stimulus_path: str, 
    add_gap: bool = True, 
    gap_ms: int = 120, 
    fs_out: int = 44100
) -> np.ndarray:
    """
    Concatenate two WAVs as cached mono int16 arrays (optionally with a silence gap).
    
    Args:
        prefix_path: Path to the prefix WAV
        stimulus_path: Path to the stimulus WAV
        add_gap: Whether to add silence gap between the two
        gap_ms: Gap duration in milliseconds
        fs_out: Target sample rate
        
    Returns:
        Concatenated PCM data as int16 array
    """
    key = (os.path.abspath(prefix_path), os.path.abspath(stimulus_path), bool(add_gap), int(gap_ms), int(fs_out))
    cached = _CONCAT_CACHE.get(key)
    if cached is not None:
        return cached

    prefix_pcm = get_pcm16_mono(prefix_path, fs_out)
    stim_pcm = get_pcm16_mono(stimulus_path, fs_out)

    if add_gap and gap_ms > 0:
        gap_samples = int(round(fs_out * (gap_ms / 1000.0)))
        silence = np.zeros((gap_samples,), dtype=np.int16)
        out = np.concatenate([prefix_pcm, silence, stim_pcm])
    else:
        out = np.concatenate([prefix_pcm, stim_pcm])

    _CONCAT_CACHE[key] = out
    return out


def clear_audio_cache() -> None:
    """Clear all cached audio data."""
    _PCM_CACHE.clear()
    _CONCAT_CACHE.clear()


# =============================================================================
# AUDIO ENGINE (Real-time playback)
# =============================================================================
class AudioEngine:
    def __init__(self, device_index: int, samplerate: int = 44100, blocksize: int = 2048, latency: str = "default"):
        self.device = device_index
        self.fs = samplerate
        self.blocksize = blocksize
        self._started_at = time.perf_counter()
        self._stream_closed = False
        self._diag_printed = False
        self._callback_status_counts = {
            "output_underflow": 0,
            "output_overflow": 0,
            "input_underflow": 0,
            "input_overflow": 0,
            "priming_output": 0,
            "other_status": 0,
        }

        self._lock = threading.Lock()
        # Voices:
        # - oneshot: used for trial stimuli (sets _done when finished)
        # - background: looping background noise (e.g., level test)
        # - target: looping target sound (e.g., level test)
        self._voices = {
            "oneshot": {"buf": np.zeros((0, 1), dtype=np.int16), "pos": 0, "active": False, "loop": False},
            "background": {"buf": np.zeros((0, 1), dtype=np.int16), "pos": 0, "active": False, "loop": True},
            "target": {"buf": np.zeros((0, 1), dtype=np.int16), "pos": 0, "active": False, "loop": True},
        }

        self._done = threading.Event()  # oneshot completion

        def callback(outdata, frames, time_info, status):
            if status:
                if getattr(status, "output_underflow", False):
                    self._callback_status_counts["output_underflow"] += 1
                if getattr(status, "output_overflow", False):
                    self._callback_status_counts["output_overflow"] += 1
                if getattr(status, "input_underflow", False):
                    self._callback_status_counts["input_underflow"] += 1
                if getattr(status, "input_overflow", False):
                    self._callback_status_counts["input_overflow"] += 1
                if getattr(status, "priming_output", False):
                    self._callback_status_counts["priming_output"] += 1

                if not any([
                    getattr(status, "output_underflow", False),
                    getattr(status, "output_overflow", False),
                    getattr(status, "input_underflow", False),
                    getattr(status, "input_overflow", False),
                    getattr(status, "priming_output", False),
                ]):
                    self._callback_status_counts["other_status"] += 1

            with self._lock:
                mix = np.zeros((frames,), dtype=np.float32)

                for name, v in self._voices.items():
                    if not v["active"]:
                        continue

                    buf = v["buf"]
                    if buf.size == 0:
                        v["active"] = False
                        v["pos"] = 0
                        if name == "oneshot":
                            self._done.set()
                        continue

                    pos = int(v["pos"])
                    n_total = buf.shape[0]

                    if not v["loop"]:
                        remaining = n_total - pos
                        n = min(frames, remaining)
                        if n > 0:
                            mix[:n] += (buf[pos:pos + n, 0].astype(np.float32) / 32768.0)
                            v["pos"] = pos + n
                        if n < frames:
                            v["active"] = False
                            v["pos"] = 0
                            if name == "oneshot":
                                self._done.set()
                        continue

                    # Looping voice
                    written = 0
                    while written < frames:
                        remaining = n_total - pos
                        n = min(frames - written, remaining)
                        if n > 0:
                            mix[written:written + n] += (buf[pos:pos + n, 0].astype(np.float32) / 32768.0)
                            written += n
                            pos += n
                        if pos >= n_total:
                            pos = 0
                    v["pos"] = pos

                mix = np.clip(mix, -1.0, 1.0)
                outdata[:, 0] = (mix * 32767.0).astype(np.int16)

        dev_info = query_devices(self.device)
        hostapi_name = query_hostapis(dev_info["hostapi"])["name"]
        host_upper = hostapi_name.upper()
        is_asio = "ASIO" in host_upper
        is_wasapi = "WASAPI" in host_upper

        if FORCE_WASAPI_OR_ASIO_EXCLUSIVE and platform.system() == "Windows":
            if not (is_asio or is_wasapi):
                raise RuntimeError(
                    f"Host API '{hostapi_name}' not allowed. "
                    "Experiment requires ASIO or WASAPI exclusive mode."
                )

        # Use exclusive WASAPI only when the experiment is configured to require it.
        if is_wasapi and FORCE_WASAPI_OR_ASIO_EXCLUSIVE and platform.system() == "Windows":
            extra = WasapiSettings(exclusive=True)
            exclusive_active = True
        else:
            extra = None
            exclusive_active = False

        # Build an ordered list of sample rates to try:
        # 1) The requested rate, 2) common alternatives.
        # This handles cases where the device's reported default_samplerate
        # doesn't match its actual hardware configuration (common with
        # MOTU + WASAPI exclusive).
        _FALLBACK_RATES = [44100, 48000, 96000, 88200, 192000]
        rates_to_try = [self.fs] + [r for r in _FALLBACK_RATES if r != self.fs]

        last_err = None
        for try_fs in rates_to_try:
            try:
                self.stream = OutputStream(
                    device=self.device,
                    samplerate=try_fs,
                    channels=1,
                    dtype="int16",
                    callback=callback,
                    blocksize=self.blocksize, 
                    latency=latency,
                    extra_settings=extra,
                )
                self.stream.start()
                if try_fs != self.fs:
                    print(f"Sample rate {self.fs} Hz rejected; using {try_fs} Hz instead", flush=True)
                self.fs = try_fs  # update to the rate that actually worked
                last_err = None
                break
            except Exception as e:
                last_err = e
                err_msg = str(e).lower()
                # Retry on any error that could be rate-related.
                # WASAPI exclusive often gives generic "unanticipated host error"
                # or "Error opening OutputStream" when the rate doesn't match.
                retryable_keywords = [
                    "sample rate", "samplerate", "invalid",
                    "unanticipated host error", "error opening",
                ]
                if any(kw in err_msg for kw in retryable_keywords):
                    print(f"  Rate {try_fs} Hz failed on '{dev_info['name']}': {e} — trying next...", flush=True)
                    continue
                # Non-rate error — stop retrying
                print(f"  Non-retryable error at {try_fs} Hz: {e}", flush=True)
                break

        if last_err is not None:
            if FORCE_WASAPI_OR_ASIO_EXCLUSIVE and platform.system() == "Windows":
                raise RuntimeError(
                    f"Failed to open exclusive audio stream on '{dev_info['name']}' "
                    f"({hostapi_name}). Tried rates {rates_to_try}: {last_err}"
                ) from last_err
            raise last_err

        print(f"Audio device: {dev_info['name']}", flush=True)
        print(f"Host API: {hostapi_name}", flush=True)
        print(f"Sample rate: {self.fs}", flush=True)
        print(f"Exclusive mode: {exclusive_active}", flush=True)
        atexit.register(self._print_stream_diagnostics)

    def _print_stream_diagnostics(self):
        if self._diag_printed:
            return
        self._diag_printed = True
        runtime_s = time.perf_counter() - self._started_at
        print("Audio callback diagnostics:", flush=True)
        print(f"  Runtime (s): {runtime_s:.2f}", flush=True)
        print(f"  output_underflow: {self._callback_status_counts['output_underflow']}", flush=True)
        print(f"  output_overflow: {self._callback_status_counts['output_overflow']}", flush=True)
        print(f"  input_underflow: {self._callback_status_counts['input_underflow']}", flush=True)
        print(f"  input_overflow: {self._callback_status_counts['input_overflow']}", flush=True)
        print(f"  priming_output: {self._callback_status_counts['priming_output']}", flush=True)
        if self._callback_status_counts["other_status"]:
            print(f"  other_status: {self._callback_status_counts['other_status']}", flush=True)

    def play(self, pcm16_mono: np.ndarray) -> int:
        """
        Start playback. Returns duration in ms.
        pcm16_mono: shape (N,) or (N,1), dtype int16.
        """
        if pcm16_mono.ndim == 1:
            pcm16_mono = pcm16_mono[:, None]
        pcm16_mono = np.asarray(pcm16_mono, dtype=np.int16)

        playback_pcm = pcm16_mono
        original_duration_ms = int(round(1000.0 * (pcm16_mono.shape[0] / self.fs)))

        lead_segment = None
        if (
            SHORT_STIMULUS_FADEIN_ENABLED
            and pcm16_mono.shape[0] > 1
            and original_duration_ms <= int(SHORT_STIMULUS_FADEIN_MAX_STIM_MS)
        ):
            fadein_samples = int(round(self.fs * (float(SHORT_STIMULUS_FADEIN_MS) / 1000.0)))
            fadein_samples = max(0, fadein_samples)
            if fadein_samples > 0:
                first_sample = int(pcm16_mono[0, 0])
                # Raised cosine (Hann) ramp: gentler acceleration, no abrupt rate changes
                t = np.linspace(0.0, 1.0, fadein_samples, dtype=np.float32)
                lead_ramp = 0.5 * (1.0 - np.cos(np.pi * t))
                lead_segment = np.round(first_sample * lead_ramp).astype(np.int16)[:, None]

        tail_segment = None
        if (
            SHORT_STIMULUS_FADEOUT_ENABLED
            and pcm16_mono.shape[0] > 1
            and original_duration_ms <= int(SHORT_STIMULUS_FADEOUT_MAX_STIM_MS)
        ):
            fadeout_samples = int(round(self.fs * (float(SHORT_STIMULUS_FADEOUT_MS) / 1000.0)))
            fadeout_samples = max(0, fadeout_samples)
            if fadeout_samples > 0:
                last_sample = int(pcm16_mono[-1, 0])
                # Raised cosine (Hann) ramp: gentler deceleration, no abrupt rate changes
                t = np.linspace(0.0, 1.0, fadeout_samples, dtype=np.float32)
                tail_ramp = 0.5 * (1.0 + np.cos(np.pi * t))
                tail_segment = np.round(last_sample * tail_ramp).astype(np.int16)[:, None]

        segments = []
        if lead_segment is not None:
            segments.append(lead_segment)
        segments.append(pcm16_mono)
        if tail_segment is not None:
            segments.append(tail_segment)
        if len(segments) > 1:
            playback_pcm = np.concatenate(segments, axis=0)

        duration_ms = int(round(1000.0 * (playback_pcm.shape[0] / self.fs)))

        with self._lock:
            v = self._voices["oneshot"]
            v["buf"] = playback_pcm
            v["pos"] = 0
            v["active"] = True
            v["loop"] = False
            self._done.clear()

        return duration_ms

    def wait_done(self, timeout: float | None = None) -> bool:
        return self._done.wait(timeout=timeout)

    def stop(self):
        with self._lock:
            for v in self._voices.values():
                v["active"] = False
                v["pos"] = 0
                v["buf"] = np.zeros((0, 1), dtype=np.int16)
            self._done.set()

    def start_loop(self, name: str, pcm16_mono: np.ndarray):
        """Start (or replace) a looping voice. Valid names: 'background', 'target'."""
        if name not in self._voices or name == "oneshot":
            raise ValueError("loop name must be 'background' or 'target'")

        if pcm16_mono.ndim == 1:
            pcm16_mono = pcm16_mono[:, None]
        pcm16_mono = np.asarray(pcm16_mono, dtype=np.int16)

        with self._lock:
            v = self._voices[name]
            v["buf"] = pcm16_mono
            v["pos"] = 0
            v["active"] = True
            v["loop"] = True

    def stop_loop(self, name: str):
        if name not in self._voices or name == "oneshot":
            raise ValueError("loop name must be 'background' or 'target'")
        with self._lock:
            v = self._voices[name]
            v["active"] = False
            v["pos"] = 0

    def is_looping(self, name: str) -> bool:
        if name not in self._voices or name == "oneshot":
            raise ValueError("loop name must be 'background' or 'target'")
        with self._lock:
            return bool(self._voices[name]["active"])

    def close(self):
        if self._stream_closed:
            self._print_stream_diagnostics()
            return

        self.stop()
        try:
            self.stream.stop()
        except Exception:
            pass
        try:
            self.stream.close()
        except Exception:
            pass

        self._stream_closed = True
        self._print_stream_diagnostics()

    def shutdown(self):
        """Compatibility alias used by end-of-experiment cleanup."""
        self.close()
