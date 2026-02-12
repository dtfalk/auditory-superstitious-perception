"""
Intro Subtimeline
=================
Handles the experiment introduction and explanation screens.

Uses displayEngine for all rendering - no dependency on helperFunctions.py
"""

import os
import sys
import wave
import numpy as np
from scipy.signal import resample_poly
import pygame as pg

# Add parent directory for imports
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE_DIR)
sys.path.insert(0, os.path.join(_BASE_DIR, 'experiment_helpers'))
sys.path.insert(0, os.path.join(_BASE_DIR, 'utils'))

from displayEngine import (
    Screen, TextRenderer, Button, ButtonStyle,
    Colors, TextStyle, TextAlign,
)
from audioEngine import AudioEngine
from text_blocks.experimentTextBlocks import (
    explanationText_1, explanationText_2, explanationText_3,
    explanationText_4, explanationText_5, audioLevelTestInstructions,
)


# =============================================================================
# AUDIO CACHING UTILITIES
# =============================================================================

_PCM_CACHE: dict[tuple[str, int], np.ndarray] = {}


def _load_wav_mono_int16(path: str) -> tuple[np.ndarray, int]:
    """Load a WAV file as mono int16."""
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


def _resample_int16(x16: np.ndarray, fs_in: int, fs_out: int) -> np.ndarray:
    """Resample int16 audio."""
    if fs_in == fs_out:
        return x16

    x = x16.astype(np.float32) / 32768.0
    g = np.gcd(fs_in, fs_out)
    y = resample_poly(x, fs_out // g, fs_in // g)
    y = np.clip(y, -1.0, 1.0)
    return (y * 32767.0).astype(np.int16)


def _get_pcm16_mono(path: str, fs_out: int) -> np.ndarray:
    """Load a WAV once, convert to mono int16, resample to fs_out, and cache."""
    key = (os.path.abspath(path), int(fs_out))
    pcm = _PCM_CACHE.get(key)
    if pcm is not None:
        return pcm

    x16, fs_in = _load_wav_mono_int16(path)
    y16 = _resample_int16(x16, fs_in, fs_out)
    _PCM_CACHE[key] = y16
    return y16


def _preload_pcm16_mono(paths: list[str], fs_out: int) -> None:
    """Best-effort preload of multiple WAV paths into the cache."""
    for p in paths:
        if p and os.path.exists(p):
            _get_pcm16_mono(p, fs_out)


def _get_stimuli_paths() -> tuple[list[str], list[str], list[str], list[str]]:
    """Get all stimuli file paths."""
    stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')
    
    full_sentence_targets = [
        os.path.join(stimuli_dir, 'full_sentence', 'targets', f)
        for f in os.listdir(os.path.join(stimuli_dir, 'full_sentence', 'targets'))
    ]
    full_sentence_distractors = [
        os.path.join(stimuli_dir, 'full_sentence', 'distractors', f)
        for f in os.listdir(os.path.join(stimuli_dir, 'full_sentence', 'distractors'))
    ]
    imagined_sentence_targets = [
        os.path.join(stimuli_dir, 'imagined_sentence', 'targets', f)
        for f in os.listdir(os.path.join(stimuli_dir, 'imagined_sentence', 'targets'))
    ]
    imagined_sentence_distractors = [
        os.path.join(stimuli_dir, 'imagined_sentence', 'distractors', f)
        for f in os.listdir(os.path.join(stimuli_dir, 'imagined_sentence', 'distractors'))
    ]
    
    return (
        full_sentence_targets, full_sentence_distractors,
        imagined_sentence_targets, imagined_sentence_distractors
    )


def preload_audio(audio_engine: AudioEngine) -> None:
    """Preload all experiment audio into cache."""
    fs_out = int(audio_engine.fs)
    audio_stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')
    
    (full_sentence_targets, full_sentence_distractors,
     imagined_sentence_targets, imagined_sentence_distractors) = _get_stimuli_paths()
    
    extras = [
        os.path.join(audio_stimuli_dir, 'fullsentenceminuswall.wav'),
        os.path.join(audio_stimuli_dir, 'fullsentence.wav'),
        os.path.join(audio_stimuli_dir, 'targetwall.wav'),
        os.path.join(audio_stimuli_dir, 'target_example.wav'),
        os.path.join(audio_stimuli_dir, 'distractor_example.wav'),
        os.path.join(audio_stimuli_dir, '60s_background_noise.wav'),
    ]
    
    _preload_pcm16_mono(
        full_sentence_targets
        + full_sentence_distractors
        + imagined_sentence_targets
        + imagined_sentence_distractors
        + extras,
        fs_out,
    )


# =============================================================================
# EXPLANATION SCREENS
# =============================================================================

def _show_explanation_page(
    win: pg.Surface,
    text: str,
) -> None:
    """Display an explanation page and wait for spacebar."""
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    style = TextStyle(
        font_size=screen.scaled_font_size(20),
        color=Colors.BLACK,
        align=TextAlign.LEFT,
    )
    
    while True:
        screen.fill()
        pg.mouse.set_visible(False)
        
        text_renderer.draw_text_block(
            text,
            rel_x=0.05,
            rel_y=0.05,
            max_width=screen.abs_x(0.90),
            style=style,
        )
        
        screen.update()
        
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()
                elif event.key == pg.K_SPACE:
                    return


def run_intro(win: pg.Surface) -> None:
    """Run the experiment introduction/explanation screens."""
    explanation_pages = [
        explanationText_1,
        explanationText_2,
        explanationText_3,
        explanationText_4,
        explanationText_5,
    ]
    
    for page_text in explanation_pages:
        _show_explanation_page(win, page_text)
    
    pg.event.clear()


# =============================================================================
# AUDIO LEVEL TEST
# =============================================================================

def run_audio_level_test(win: pg.Surface, audio_engine: AudioEngine) -> None:
    """
    Show audio level testing screen for the experimenter to normalize audio levels.
    Allows playing background noise and target sounds with start/stop controls.
    """
    pg.mouse.set_visible(True)
    
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    # Load audio files
    audio_stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')
    fs_out = int(audio_engine.fs)
    
    target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    background_noise_path = os.path.join(audio_stimuli_dir, '60s_background_noise.wav')
    
    target_pcm = _get_pcm16_mono(target_path, fs_out)
    background_pcm = _get_pcm16_mono(background_noise_path, fs_out)
    
    background_playing = False
    target_playing = False
    
    # Button styles
    start_style = ButtonStyle(bg_color=Colors.GREEN, text_color=Colors.BLACK)
    stop_style = ButtonStyle(bg_color=Colors.RED, text_color=Colors.WHITE)
    continue_style = ButtonStyle(bg_color=Colors.BLUE, text_color=Colors.WHITE)
    
    while True:
        screen.fill()
        
        # Draw instructions
        title_style = TextStyle(
            font_size=screen.scaled_font_size(25),
            color=Colors.BLACK,
            align=TextAlign.CENTER,
        )
        text_renderer.draw_centered_text(
            "Audio Level Test",
            rel_y=0.1,
            style=title_style,
        )
        
        instruction_style = TextStyle(
            font_size=screen.scaled_font_size(18),
            color=Colors.BLACK,
            align=TextAlign.CENTER,
        )
        
        instructions = [
            "Use the buttons below to play audio and adjust system volume.",
            "Adjust until the audio is at a comfortable listening level.",
            "Click Continue when ready.",
        ]
        
        y = 0.18
        for line in instructions:
            text_renderer.draw_centered_text(line, rel_y=y, style=instruction_style)
            y += 0.05
        
        # Create buttons with current states
        bg_text = "Stop Background" if background_playing else "Start Background"
        bg_style = stop_style if background_playing else start_style
        
        target_text = "Stop Target" if target_playing else "Start Target"
        target_style = stop_style if target_playing else start_style
        
        background_btn = Button(
            screen, bg_text,
            rel_x=0.25, rel_y=0.5,
            rel_width=0.2, rel_height=0.08,
            style=bg_style,
        )
        
        target_btn = Button(
            screen, target_text,
            rel_x=0.75, rel_y=0.5,
            rel_width=0.2, rel_height=0.08,
            style=target_style,
        )
        
        continue_btn = Button(
            screen, "Continue",
            rel_x=0.5, rel_y=0.8,
            rel_width=0.15, rel_height=0.06,
            style=continue_style,
        )
        
        mouse_pos = pg.mouse.get_pos()
        
        background_btn.update_state(mouse_pos)
        target_btn.update_state(mouse_pos)
        continue_btn.update_state(mouse_pos)
        
        background_btn.draw()
        target_btn.draw()
        continue_btn.draw()
        
        screen.update()
        
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()
            
            elif event.type == pg.MOUSEBUTTONUP:
                if background_btn.is_clicked(mouse_pos, True):
                    if background_playing:
                        audio_engine.stop_loop('background')
                        background_playing = False
                    else:
                        audio_engine.start_loop('background', background_pcm)
                        background_playing = True
                
                elif target_btn.is_clicked(mouse_pos, True):
                    if target_playing:
                        audio_engine.stop_loop('target')
                        target_playing = False
                    else:
                        audio_engine.start_loop('target', target_pcm)
                        target_playing = True
                
                elif continue_btn.is_clicked(mouse_pos, True):
                    # Stop all audio when exiting
                    if background_playing:
                        audio_engine.stop_loop('background')
                    if target_playing:
                        audio_engine.stop_loop('target')
                    return
