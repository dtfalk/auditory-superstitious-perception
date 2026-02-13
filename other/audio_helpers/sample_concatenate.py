import wave 
import os
import io
import pygame as pg
import soundfile as sf
import numpy as np

def concatenate_wavs(prefix_path, stimulus_path, add_gap=True, gap_ms=120):
    with wave.open(prefix_path, 'rb') as w1, wave.open(stimulus_path, 'rb') as w2:
        p1, p2 = w1.getparams(), w2.getparams()

        # Compare actual format fields (not nframes)
        fmt1 = (p1.nchannels, p1.sampwidth, p1.framerate, p1.comptype)
        fmt2 = (p2.nchannels, p2.sampwidth, p2.framerate, p2.comptype)
        if fmt1 != fmt2:
            raise ValueError(f"WAV format mismatch: {fmt1} vs {fmt2}")

        prefix_frames = w1.readframes(p1.nframes)
        stim_frames = w2.readframes(p2.nframes)

        if add_gap and gap_ms > 0:
            # Compute silence length in frames and bytes
            gap_frames = int(round(p1.framerate * (gap_ms / 1000.0)))
            bytes_per_frame = p1.sampwidth * p1.nchannels
            silence = b'\x00' * (gap_frames * bytes_per_frame)
            frames = prefix_frames + silence + stim_frames
        else:
            frames = prefix_frames + stim_frames

        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as out:
            out.setparams(p1)  # preserve original format
            out.writeframes(frames)

        buffer.seek(0)
        return pg.mixer.Sound(buffer)

def save_pg_sound_to_wav(sound: pg.mixer.Sound, out_path: str):
    """
    Save a pygame.mixer.Sound to a WAV file.
    Preserves sample rate, channels, and level.
    """

    # Get raw samples as numpy array
    arr = pg.sndarray.array(sound)

    # pygame returns int16 by default
    if arr.dtype != np.int16:
        arr = arr.astype(np.int16)

    # Get mixer settings
    freq, fmt, channels = pg.mixer.get_init()

    # Normalize shape for soundfile
    if channels == 1:
        data = arr
    else:
        # pygame uses (samples, channels)
        data = arr

    # Write WAV
    sf.write(
        out_path,
        data,
        samplerate=freq,
        subtype="PCM_16"
    )

    print(f"Saved pygame Sound → WAV: {out_path}")

if __name__ == "__main__":
    pg.mixer.init()
    high_freq_prefix_wav = os.path.join(os.path.dirname(__file__), "..", "audio_stimuli", "fullsentenceminuswall_high_frequency.wav")
    high_freq_sample_wav = os.path.join(os.path.dirname(__file__), "..", "audio_stimuli", "44khz", "targets", "chunk_24479.wav")

    low_freq_prefix_wav = os.path.join(os.path.dirname(__file__), "..", "audio_stimuli", "fullsentenceminuswall_low_frequency.wav")
    low_freq_sample_wav = os.path.join(os.path.dirname(__file__), "..", "audio_stimuli", "8khz", "targets", "chunk_15751.wav")
    
    high_freq_sound = concatenate_wavs(high_freq_prefix_wav, high_freq_sample_wav)
    save_pg_sound_to_wav(high_freq_sound, os.path.join(os.path.dirname(__file__), "high_freq_example.wav"))

    low_freq_sound = concatenate_wavs(low_freq_prefix_wav, low_freq_sample_wav)
    save_pg_sound_to_wav(low_freq_sound, os.path.join(os.path.dirname(__file__), "low_freq_example.wav"))

