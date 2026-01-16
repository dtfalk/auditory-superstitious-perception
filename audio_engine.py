# audio_engine.py
import threading
import numpy as np
import sounddevice as sd

class AudioEngine:
    def __init__(self, device_index: int, samplerate: int = 44100, blocksize: int = 256):
        self.device = device_index
        self.fs = samplerate
        self.blocksize = blocksize

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
                # If you want, log status to a file for debugging
                pass

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

        dev_info = sd.query_devices(self.device)
        hostapi_name = sd.query_hostapis(dev_info["hostapi"])["name"]
        use_wasapi = "WASAPI" in hostapi_name.upper()

        extra = sd.WasapiSettings(exclusive=True) if use_wasapi else None

        self.stream = sd.OutputStream(
            device=self.device,
            samplerate=self.fs,
            channels=1,
            dtype="int16",
            callback=callback,
            blocksize=self.blocksize,
            latency="low",
            extra_settings=extra,
        )
        self.stream.start()

    def play(self, pcm16_mono: np.ndarray) -> int:
        """
        Start playback. Returns duration in ms.
        pcm16_mono: shape (N,) or (N,1), dtype int16.
        """
        if pcm16_mono.ndim == 1:
            pcm16_mono = pcm16_mono[:, None]
        pcm16_mono = np.asarray(pcm16_mono, dtype=np.int16)

        with self._lock:
            v = self._voices["oneshot"]
            v["buf"] = pcm16_mono
            v["pos"] = 0
            v["active"] = True
            v["loop"] = False
            self._done.clear()

        duration_ms = int(round(1000.0 * (pcm16_mono.shape[0] / self.fs)))
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
        self.stop()
        self.stream.stop()
        self.stream.close()
