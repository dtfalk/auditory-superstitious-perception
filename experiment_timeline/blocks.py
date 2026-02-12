"""
Blocks Subtimeline
==================
Handles block-level experiment flow including:
- Block randomization
- Block instructions
- Target familiarization
- Trial loop
- Periodic reminders
- Self-reflection questions

Uses displayEngine and audioEngine - no dependency on helperFunctions.py
"""

import os
import sys
import csv
import time
import wave
import numpy as np
from random import shuffle, choice
from scipy.signal import resample_poly
import pygame as pg

# Add parent directory for imports
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE_DIR)
sys.path.insert(0, os.path.join(_BASE_DIR, 'experiment_helpers'))
sys.path.insert(0, os.path.join(_BASE_DIR, 'utils'))

from displayEngine import (
    Screen, TextRenderer, TextInput, Button, ButtonStyle,
    Colors, TextStyle, TextAlign, InputMode,
)
from audioEngine import AudioEngine
from experimenterLevers import MAX_PLAYS, REMINDER_INTERVAL, FAMILIARIZATION_MAX_PLAYS, REMINDER_MAX_PLAYS
from text_blocks.experimentTextBlocks import (
    fullSentenceBlockInstructionsText, imaginedSentenceBlockInstructionsText,
    preTrialQuickResponseTextFullSentence, preTrialQuickResponseTextImaginedSentence,
    trialInstructions_full_sentence, trialInstructions_imagined_sentence,
    preExamplesFamiliarizationInstructions_full_sentence, preExamplesFamiliarizationInstructions_imagined_sentence,
    targetFamiliarizationInstructions_full_sentence, targetFamiliarizationInstructions_imagined_sentence,
    periodicReminderInstructions_full_sentence, periodicReminderInstructions_imagined_sentence,
    blockExamplesInstructions_imagined_sentence, blockExamplesInstructions_full_sentence,
    breakScreenText,
)


# =============================================================================
# AUDIO UTILITIES
# =============================================================================

_PCM_CACHE: dict[tuple[str, int], np.ndarray] = {}
_CONCAT_CACHE: dict[tuple, np.ndarray] = {}


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


def _concatenate_wavs(prefix_wav: str, stim_wav: str, add_gap: bool, fs_out: int, gap_ms: int = 0) -> np.ndarray:
    """Concatenate two WAV files."""
    key = (os.path.abspath(prefix_wav), os.path.abspath(stim_wav), add_gap, gap_ms, fs_out)
    cached = _CONCAT_CACHE.get(key)
    if cached is not None:
        return cached

    prefix_pcm = _get_pcm16_mono(prefix_wav, fs_out)
    stim_pcm = _get_pcm16_mono(stim_wav, fs_out)

    if add_gap and gap_ms > 0:
        gap_samples = int(fs_out * gap_ms / 1000.0)
        gap = np.zeros(gap_samples, dtype=np.int16)
        out = np.concatenate([prefix_pcm, gap, stim_pcm])
    else:
        out = np.concatenate([prefix_pcm, stim_pcm])

    _CONCAT_CACHE[key] = out
    return out


def _play_audio_stimulus(audio_engine: AudioEngine, pcm16: np.ndarray) -> int:
    """Play audio and return duration in ms."""
    return audio_engine.play(pcm16)


# =============================================================================
# STIMULI MANAGEMENT
# =============================================================================

def _get_stimuli() -> tuple[list[str], list[str], list[str], list[str]]:
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

    return (full_sentence_targets, full_sentence_distractors,
            imagined_sentence_targets, imagined_sentence_distractors)


def _select_stimulus(
    targets: list[str],
    distractors: list[str],
    prefix_wav: str | None,
    fs_out: int
) -> tuple[np.ndarray, str, str]:
    """Select a random stimulus and remove it from its list."""
    master_list = targets + distractors
    stimulus = choice(master_list)

    if stimulus in targets:
        stimulus_type = 'target'
        targets.remove(stimulus)
    else:
        stimulus_type = 'distractor'
        distractors.remove(stimulus)

    # If prefix_wav is provided, concatenate; otherwise use stimulus as-is
    if prefix_wav:
        sound = _concatenate_wavs(prefix_wav, stimulus, add_gap=False, fs_out=fs_out)
    else:
        sound = _get_pcm16_mono(stimulus, fs_out)

    filename = os.path.splitext(os.path.basename(stimulus))[0]
    return sound, filename, stimulus_type


def _record_response(
    subject_number: str,
    block: str,
    stimulus_number: str,
    stimulus_type: str,
    response: str,
    response_time: float,
    save_folder: str,
    play_count: int = 1
) -> None:
    """Record a trial response."""
    filepath = os.path.join(save_folder, f'{block}_{subject_number}.csv')

    header = ['Subject Number', 'Block Scheme', 'Stimulus Number', 'Stimulus Type', 
              'Subject Response', 'Response Time', 'Play Count']
    data = [subject_number, block, stimulus_number, stimulus_type, response, 
            f'{response_time / 1000:.5f}', play_count]

    file_exists = os.path.exists(filepath)
    with open(filepath, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(data)


# =============================================================================
# DISPLAY UTILITIES
# =============================================================================

def _show_text_page(win: pg.Surface, text: str, wait_key: int = pg.K_SPACE) -> None:
    """Display a page of text and wait for a key press."""
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
                elif event.key == wait_key:
                    return


def _show_centered_instructions(win: pg.Surface, instructions: list[str]) -> int:
    """Draw centered instructions and return the y position after the last line."""
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    style = TextStyle(
        font_size=screen.scaled_font_size(18),
        color=Colors.BLACK,
        align=TextAlign.CENTER,
    )
    
    y = 0.05
    for line in instructions:
        if line:
            text_renderer.draw_centered_text(line, rel_y=y, style=style)
        y += 0.04
    
    return screen.abs_y(y)


# =============================================================================
# TRIAL INTERFACE
# =============================================================================

def _draw_audio_interface(
    win: pg.Surface,
    play_count: int,
    max_plays: int,
    audio_played: bool = False,
    can_play: bool = True,
    can_respond: bool = True,
    block_name: str | None = None,
) -> pg.Rect:
    """Draw the audio interface with instructions and play button."""
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    screen.fill()

    # Get block-specific instructions
    if block_name == 'imagined_sentence':
        instructions = list(trialInstructions_imagined_sentence)
    else:
        instructions = list(trialInstructions_full_sentence)

    # Draw instructions
    instruction_style = TextStyle(
        font_size=screen.scaled_font_size(22),
        color=Colors.BLACK,
        align=TextAlign.CENTER,
    )
    
    y = 0.08
    max_y = 0.45  # Don't let instructions overlap with button
    
    for line in instructions:
        if y >= max_y:
            break
        if line:
            text_renderer.draw_centered_text(line, rel_y=y, style=instruction_style)
        y += 0.05

    # Create play button
    button_width = screen.abs_x(0.18)
    button_height = screen.abs_y(0.08)
    button_x = (screen.width - button_width) // 2
    button_y = screen.abs_y(0.55)
    button_rect = pg.Rect(button_x, button_y, button_width, button_height)

    # Draw play button
    enabled = play_count < max_plays and can_play
    if not can_play:
        color = Colors.BLUE.darken(0.5)
        text_color = Colors.GRAY
    elif not enabled:
        color = Colors.GRAY
        text_color = Colors.BLACK
    else:
        color = Colors.BLUE
        text_color = Colors.WHITE

    pg.draw.rect(win, color.to_tuple(), button_rect)
    pg.draw.rect(win, Colors.BLACK.to_tuple(), button_rect, 3)

    font = pg.font.SysFont("times new roman", max(18, screen.height // 35))
    text_surface = font.render("Play Audio", True, text_color.to_tuple())
    text_rect = text_surface.get_rect(center=button_rect.center)
    win.blit(text_surface, text_rect)

    return button_rect


# =============================================================================
# FAMILIARIZATION & REMINDER SCREENS
# =============================================================================

def _show_pre_examples_familiarization(
    win: pg.Surface,
    subject_number: str,
    save_folder: str,
    block_name: str,
    audio_engine: AudioEngine,
) -> None:
    """Show the pre-examples target familiarization screen."""
    pg.mouse.set_visible(True)
    screen = Screen(win)
    
    # Load target sound
    audio_stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')
    actual_target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    fs_out = int(audio_engine.fs)
    actual_target_pcm = _get_pcm16_mono(actual_target_path, fs_out)

    required_plays = 5
    play_count = 0
    last_audio_start = 0
    audio_duration = int(round(1000.0 * (actual_target_pcm.shape[0] / fs_out)))

    # Get instructions based on block
    if block_name == "full_sentence":
        instructions = preExamplesFamiliarizationInstructions_full_sentence
    else:
        instructions = preExamplesFamiliarizationInstructions_imagined_sentence

    while True:
        screen.fill()
        current_time = pg.time.get_ticks()
        time_since_last = current_time - last_audio_start
        can_play = (last_audio_start == 0) or (time_since_last >= audio_duration + 250)
        audio_still_playing = (last_audio_start != 0) and (time_since_last < audio_duration)
        continue_enabled = (play_count >= required_plays) and (not audio_still_playing)

        # Draw instructions
        y_pos = _show_centered_instructions(win, instructions)

        # Create buttons
        btn_y = y_pos + screen.abs_y(0.1)
        btn_width = screen.abs_x(0.2)
        btn_height = screen.abs_y(0.08)
        cont_width = screen.abs_x(0.15)
        cont_height = screen.abs_y(0.06)

        play_rect = pg.Rect((screen.width - btn_width) // 2, btn_y, btn_width, btn_height)
        cont_rect = pg.Rect((screen.width - cont_width) // 2, btn_y + btn_height + 20, cont_width, cont_height)

        # Draw play button
        if can_play and play_count < required_plays * 10:  # Allow many plays
            play_color = Colors.BLUE
            play_text_color = Colors.WHITE
        else:
            play_color = Colors.GRAY
            play_text_color = Colors.BLACK

        pg.draw.rect(win, play_color.to_tuple(), play_rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), play_rect, 3)

        # Draw continue button
        cont_color = Colors.GREEN if continue_enabled else Colors.GRAY
        pg.draw.rect(win, cont_color.to_tuple(), cont_rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), cont_rect, 3)

        # Button text
        font = pg.font.SysFont("times new roman", max(16, screen.height // 40))
        play_text = font.render("Play Sentence", True, play_text_color.to_tuple())
        cont_text = font.render("Continue", True, Colors.BLACK.to_tuple())
        win.blit(play_text, play_text.get_rect(center=play_rect.center))
        win.blit(cont_text, cont_text.get_rect(center=cont_rect.center))

        screen.update()

        for event in pg.event.get():
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                pg.quit()
                sys.exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                mouse = pg.mouse.get_pos()
                if play_rect.collidepoint(mouse) and can_play:
                    audio_duration = _play_audio_stimulus(audio_engine, actual_target_pcm)
                    last_audio_start = current_time
                    play_count += 1
                elif cont_rect.collidepoint(mouse) and continue_enabled:
                    return


def _show_block_examples(
    win: pg.Surface,
    audio_engine: AudioEngine,
    block_name: str,
    save_folder: str,
    subject_number: str,
) -> None:
    """Show the block examples screen with target and distractor samples."""
    pg.mouse.set_visible(True)
    screen = Screen(win)
    text_renderer = TextRenderer(screen)

    # Load example files
    audio_stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')
    examples_targets_dir = os.path.join(audio_stimuli_dir, 'examples', 'targets')
    examples_distractors_dir = os.path.join(audio_stimuli_dir, 'examples', 'distractors')

    target_files = sorted([f for f in os.listdir(examples_targets_dir) if f.lower().endswith('.wav')])
    distractor_files = sorted([f for f in os.listdir(examples_distractors_dir) if f.lower().endswith('.wav')])

    fs_out = int(audio_engine.fs)
    
    # Load audio
    targets_pcm = [_get_pcm16_mono(os.path.join(examples_targets_dir, f), fs_out) for f in target_files]
    distractors_pcm = [_get_pcm16_mono(os.path.join(examples_distractors_dir, f), fs_out) for f in distractor_files]
    
    # Load actual target (full sentence)
    actual_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    actual_pcm = _get_pcm16_mono(actual_path, fs_out)

    # Tracking
    target_counts = [0] * len(target_files)
    distractor_counts = [0] * len(distractor_files)
    actual_count = 0
    last_audio_start = 0
    audio_duration = 0

    while True:
        screen.fill()
        current_time = pg.time.get_ticks()
        time_since_last = current_time - last_audio_start
        audio_still_playing = (last_audio_start != 0) and (time_since_last < audio_duration)

        # Title
        title_style = TextStyle(font_size=screen.scaled_font_size(22), color=Colors.BLACK, align=TextAlign.CENTER)
        text_renderer.draw_centered_text("Example Audio Samples", rel_y=0.03, style=title_style)
        
        if block_name == "imagined_sentence":
            subtitle = "Imagine the sentence, then click each button to hear examples"
        else:
            subtitle = "Click each button to hear examples"
        
        sub_style = TextStyle(font_size=screen.scaled_font_size(16), color=Colors.BLACK, align=TextAlign.CENTER)
        text_renderer.draw_centered_text(subtitle, rel_y=0.08, style=sub_style)

        # Create button layout
        btn_w = screen.abs_x(0.12)
        btn_h = screen.abs_y(0.06)
        
        # Actual audio button (top center)
        actual_rect = pg.Rect((screen.width - btn_w) // 2, screen.abs_y(0.15), btn_w, btn_h)
        
        # Target buttons (left column)
        target_rects = []
        for i in range(len(target_files)):
            rect = pg.Rect(screen.abs_x(0.15), screen.abs_y(0.28 + i * 0.08), btn_w, btn_h)
            target_rects.append(rect)
        
        # Distractor buttons (right column)
        distractor_rects = []
        for i in range(len(distractor_files)):
            rect = pg.Rect(screen.abs_x(0.55), screen.abs_y(0.28 + i * 0.08), btn_w, btn_h)
            distractor_rects.append(rect)
        
        # Continue button
        cont_w = screen.abs_x(0.12)
        cont_h = screen.abs_y(0.06)
        cont_rect = pg.Rect((screen.width - cont_w) // 2, screen.abs_y(0.85), cont_w, cont_h)

        # Draw buttons
        font = pg.font.SysFont("times new roman", max(14, screen.height // 50))
        
        # Actual audio
        color = Colors.BLUE if not audio_still_playing else Colors.GRAY
        pg.draw.rect(win, color.to_tuple(), actual_rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), actual_rect, 2)
        text = font.render("Full Sentence", True, Colors.WHITE.to_tuple())
        win.blit(text, text.get_rect(center=actual_rect.center))

        # Labels
        label_font = pg.font.SysFont("times new roman", max(14, screen.height // 45))
        target_label = label_font.render("Contains 'Wall':", True, Colors.BLACK.to_tuple())
        win.blit(target_label, (screen.abs_x(0.15), screen.abs_y(0.22)))
        distractor_label = label_font.render("No 'Wall':", True, Colors.BLACK.to_tuple())
        win.blit(distractor_label, (screen.abs_x(0.55), screen.abs_y(0.22)))

        # Target buttons
        for i, rect in enumerate(target_rects):
            enabled = not audio_still_playing
            color = Colors.GREEN if enabled else Colors.GRAY
            pg.draw.rect(win, color.to_tuple(), rect)
            pg.draw.rect(win, Colors.BLACK.to_tuple(), rect, 2)
            text = font.render(f"Target {i+1}", True, Colors.BLACK.to_tuple())
            win.blit(text, text.get_rect(center=rect.center))

        # Distractor buttons
        for i, rect in enumerate(distractor_rects):
            enabled = not audio_still_playing
            color = Colors.RED if enabled else Colors.GRAY
            pg.draw.rect(win, color.to_tuple(), rect)
            pg.draw.rect(win, Colors.BLACK.to_tuple(), rect, 2)
            text = font.render(f"Example {i+1}", True, Colors.WHITE.to_tuple())
            win.blit(text, text.get_rect(center=rect.center))

        # Continue button
        cont_color = Colors.GREEN if not audio_still_playing else Colors.GRAY
        pg.draw.rect(win, cont_color.to_tuple(), cont_rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), cont_rect, 2)
        cont_text = font.render("Continue", True, Colors.BLACK.to_tuple())
        win.blit(cont_text, cont_text.get_rect(center=cont_rect.center))

        screen.update()

        for event in pg.event.get():
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                pg.quit()
                sys.exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                mouse = pg.mouse.get_pos()
                
                if cont_rect.collidepoint(mouse) and not audio_still_playing:
                    # Save example play counts
                    out_path = os.path.join(save_folder, f'example_play_counts_{block_name}_{subject_number}.csv')
                    with open(out_path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(['actual_audio'] + [f'target_{i}' for i in range(len(target_files))] + 
                                       [f'distractor_{i}' for i in range(len(distractor_files))])
                        writer.writerow([actual_count] + target_counts + distractor_counts)
                    return
                
                if audio_still_playing:
                    continue
                
                if actual_rect.collidepoint(mouse):
                    audio_duration = _play_audio_stimulus(audio_engine, actual_pcm)
                    last_audio_start = current_time
                    actual_count += 1
                
                for i, rect in enumerate(target_rects):
                    if rect.collidepoint(mouse):
                        audio_duration = _play_audio_stimulus(audio_engine, targets_pcm[i])
                        last_audio_start = current_time
                        target_counts[i] += 1
                        break
                
                for i, rect in enumerate(distractor_rects):
                    if rect.collidepoint(mouse):
                        audio_duration = _play_audio_stimulus(audio_engine, distractors_pcm[i])
                        last_audio_start = current_time
                        distractor_counts[i] += 1
                        break


def _show_target_familiarization(
    win: pg.Surface,
    subject_number: str,
    save_folder: str,
    session_number: int,
    block_name: str,
    audio_engine: AudioEngine,
) -> None:
    """Show target familiarization screen before trials begin."""
    pg.mouse.set_visible(True)
    screen = Screen(win)

    # Load target sound
    audio_stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')
    actual_target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    fs_out = int(audio_engine.fs)
    actual_target_pcm = _get_pcm16_mono(actual_target_path, fs_out)

    required_plays = FAMILIARIZATION_MAX_PLAYS
    play_count = 0
    last_audio_start = 0
    audio_duration = int(round(1000.0 * (actual_target_pcm.shape[0] / fs_out)))

    if block_name == "full_sentence":
        instructions = targetFamiliarizationInstructions_full_sentence
    else:
        instructions = targetFamiliarizationInstructions_imagined_sentence

    while True:
        screen.fill()
        current_time = pg.time.get_ticks()
        time_since_last = current_time - last_audio_start
        can_play = (last_audio_start == 0) or (time_since_last >= audio_duration + 350)
        audio_still_playing = (last_audio_start != 0) and (time_since_last < audio_duration)
        continue_enabled = (play_count >= required_plays) and (not audio_still_playing)

        y_pos = _show_centered_instructions(win, instructions)

        btn_y = y_pos + screen.abs_y(0.08)
        btn_width = screen.abs_x(0.2)
        btn_height = screen.abs_y(0.08)
        cont_width = screen.abs_x(0.15)
        cont_height = screen.abs_y(0.06)

        play_rect = pg.Rect((screen.width - btn_width) // 2, btn_y, btn_width, btn_height)
        cont_rect = pg.Rect((screen.width - cont_width) // 2, btn_y + btn_height + 20, cont_width, cont_height)

        can_click_play = can_play and (play_count < required_plays)
        
        if can_click_play:
            play_color = Colors.BLUE
            play_text_color = Colors.WHITE
        elif play_count >= required_plays:
            play_color = Colors.GRAY
            play_text_color = Colors.BLACK
        else:
            play_color = Colors.BLUE.darken(0.5)
            play_text_color = Colors.GRAY

        pg.draw.rect(win, play_color.to_tuple(), play_rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), play_rect, 3)

        cont_color = Colors.GREEN if continue_enabled else Colors.GRAY
        pg.draw.rect(win, cont_color.to_tuple(), cont_rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), cont_rect, 3)

        font = pg.font.SysFont("times new roman", max(16, screen.height // 40))
        play_text_str = "Max Plays Reached" if play_count >= required_plays else "Play Sentence"
        play_text = font.render(play_text_str, True, play_text_color.to_tuple())
        cont_text = font.render("Continue", True, Colors.BLACK.to_tuple())
        win.blit(play_text, play_text.get_rect(center=play_rect.center))
        win.blit(cont_text, cont_text.get_rect(center=cont_rect.center))

        screen.update()

        for event in pg.event.get():
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                pg.quit()
                sys.exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                mouse = pg.mouse.get_pos()
                if play_rect.collidepoint(mouse) and can_click_play:
                    audio_duration = _play_audio_stimulus(audio_engine, actual_target_pcm)
                    last_audio_start = current_time
                    play_count += 1
                elif cont_rect.collidepoint(mouse) and continue_enabled:
                    # Save data
                    _save_target_familiarization_data(subject_number, save_folder, session_number, play_count, block_name)
                    return


def _save_target_familiarization_data(
    subject_number: str,
    save_folder: str,
    session_number: int,
    play_count: int,
    block_name: str,
) -> None:
    """Save target familiarization data."""
    from datetime import datetime
    
    filepath = os.path.join(save_folder, f'target_familiarization_{subject_number}.csv')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = ['Subject Number', 'Session Number', 'Block Name', 'Play Count', 'Timestamp']
    data = [subject_number, session_number, block_name, play_count, timestamp]

    file_exists = os.path.exists(filepath)
    with open(filepath, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(data)


def _show_periodic_reminder(
    win: pg.Surface,
    subject_number: str,
    save_folder: str,
    trial_number: int,
    block_name: str,
    audio_engine: AudioEngine,
) -> None:
    """Show periodic reminder screen."""
    pg.mouse.set_visible(True)
    screen = Screen(win)

    audio_stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')
    actual_target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    fs_out = int(audio_engine.fs)
    actual_target_pcm = _get_pcm16_mono(actual_target_path, fs_out)

    required_plays = REMINDER_MAX_PLAYS
    play_count = 0
    last_audio_start = 0
    audio_duration = int(round(1000.0 * (actual_target_pcm.shape[0] / fs_out)))

    if block_name == "full_sentence":
        instructions = periodicReminderInstructions_full_sentence
    else:
        instructions = periodicReminderInstructions_imagined_sentence

    while True:
        screen.fill()
        current_time = pg.time.get_ticks()
        time_since_last = current_time - last_audio_start
        can_play = (last_audio_start == 0) or (time_since_last >= audio_duration + 350)
        audio_still_playing = (last_audio_start != 0) and (time_since_last < audio_duration)
        continue_enabled = (play_count >= required_plays) and (not audio_still_playing)

        y_pos = _show_centered_instructions(win, instructions)

        btn_y = y_pos + screen.abs_y(0.08)
        btn_width = screen.abs_x(0.2)
        btn_height = screen.abs_y(0.08)
        cont_width = screen.abs_x(0.15)
        cont_height = screen.abs_y(0.06)

        play_rect = pg.Rect((screen.width - btn_width) // 2, btn_y, btn_width, btn_height)
        cont_rect = pg.Rect((screen.width - cont_width) // 2, btn_y + btn_height + 20, cont_width, cont_height)

        can_click = can_play and (play_count < required_plays)

        if can_click:
            play_color = Colors.BLUE
            play_text_color = Colors.WHITE
        elif play_count >= required_plays:
            play_color = Colors.GRAY
            play_text_color = Colors.BLACK
        else:
            play_color = Colors.BLUE.darken(0.5)
            play_text_color = Colors.GRAY

        pg.draw.rect(win, play_color.to_tuple(), play_rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), play_rect, 3)

        cont_color = Colors.GREEN if continue_enabled else Colors.GRAY
        pg.draw.rect(win, cont_color.to_tuple(), cont_rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), cont_rect, 3)

        font = pg.font.SysFont("times new roman", max(16, screen.height // 40))
        play_text_str = "Max Plays Reached" if play_count >= required_plays else "Play Sentence"
        play_text = font.render(play_text_str, True, play_text_color.to_tuple())
        cont_text = font.render("Continue", True, Colors.BLACK.to_tuple())
        win.blit(play_text, play_text.get_rect(center=play_rect.center))
        win.blit(cont_text, cont_text.get_rect(center=cont_rect.center))

        screen.update()

        for event in pg.event.get():
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                pg.quit()
                sys.exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                mouse = pg.mouse.get_pos()
                if play_rect.collidepoint(mouse) and can_click:
                    audio_duration = _play_audio_stimulus(audio_engine, actual_target_pcm)
                    last_audio_start = current_time
                    play_count += 1
                elif cont_rect.collidepoint(mouse) and continue_enabled:
                    # Save data
                    _save_periodic_reminder_data(subject_number, save_folder, trial_number, play_count, block_name)
                    return


def _save_periodic_reminder_data(
    subject_number: str,
    save_folder: str,
    trial_number: int,
    play_count: int,
    block_name: str,
) -> None:
    """Save periodic reminder data."""
    from datetime import datetime

    filepath = os.path.join(save_folder, f'periodic_reminders_{block_name}_{subject_number}.csv')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = ['Subject Number', 'Block Name', 'Trial Number (Block)', 'Play Count', 'Timestamp']
    data = [subject_number, block_name, trial_number, play_count, timestamp]

    file_exists = os.path.exists(filepath)
    with open(filepath, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(data)


# =============================================================================
# SELF-REFLECTION
# =============================================================================

def _get_subject_input(win: pg.Surface, prompt: str) -> str:
    """Get free-form text input from participant."""
    screen = Screen(win)
    text_input = TextInput(
        screen,
        mode=InputMode.FULL_ASCII,
        allow_spaces=True,
        allow_shift_symbols=True,
        placeholder="Type your response..."
    )
    result = text_input.run(prompt=prompt)
    return result if result else ""


def _save_self_reflection(
    win: pg.Surface,
    subject_number: str,
    save_folder: str,
    block_name: str
) -> None:
    """Collect and save self-reflection responses after a block."""
    explanation = _get_subject_input(
        win,
        'During the previous block, how did you decide whether or not the word "Wall" was in each of the stimuli? What were you thinking about or considering as you made that decision?\n\nResponse:'
    )
    
    changes = _get_subject_input(
        win,
        'Did your methodology change or evolve over the course of the previous block?\n\nResponse:'
    )

    if block_name == 'imagined_sentence':
        rule_following = _get_subject_input(
            win,
            'During this block did you imagine the sentence before playing the stimuli and then click "Play Audio" at the moment you would have imagined the word "Wall"? Please begin your response with either "Yes." or "No." You may include additional information after typing "Yes." or "No."\n\nResponse:'
        )
    else:
        rule_following = 'N/A'

    filepath = os.path.join(save_folder, f'self_reflection_{block_name}_{subject_number}.csv')
    with open(filepath, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Subject Number', 'Block Name', 'Methodology Explanation', 'Methodology Changes', 'Imagination Rule Following'])
        writer.writerow([subject_number, block_name, explanation, changes, rule_following])


# =============================================================================
# BLOCK INSTRUCTIONS
# =============================================================================

def _show_block_instructions(
    win: pg.Surface,
    block_name: str,
    audio_engine: AudioEngine,
    save_folder: str,
    subject_number: str,
) -> None:
    """Show block instructions, familiarization, and examples."""
    if block_name == 'imagined_sentence':
        text = imaginedSentenceBlockInstructionsText
    else:
        text = fullSentenceBlockInstructionsText

    _show_text_page(win, text, wait_key=pg.K_SPACE)
    _show_pre_examples_familiarization(win, subject_number, save_folder, block_name, audio_engine)
    _show_block_examples(win, audio_engine, block_name, save_folder, subject_number)
    pg.mouse.set_visible(False)


def _show_pre_trial_screen(win: pg.Surface, block_name: str) -> None:
    """Show pre-trial quick response screen."""
    if block_name == "full_sentence":
        text = preTrialQuickResponseTextFullSentence
    else:
        text = preTrialQuickResponseTextImaginedSentence
    
    _show_text_page(win, text, wait_key=pg.K_SPACE)


def _show_break_screen(win: pg.Surface, block_index: int) -> None:
    """Show break screen between blocks."""
    _show_text_page(win, breakScreenText, wait_key=pg.K_f)


# =============================================================================
# MAIN BLOCK FUNCTIONS
# =============================================================================

def prepare_blocks() -> tuple[list[str], dict]:
    """Prepare and randomize experimental blocks."""
    (full_sentence_targets, full_sentence_distractors,
     imagined_sentence_targets, imagined_sentence_distractors) = _get_stimuli()

    block_dictionary = {
        'full_sentence': (full_sentence_targets, full_sentence_distractors),
        'imagined_sentence': (imagined_sentence_targets, imagined_sentence_distractors)
    }

    block_names = list(block_dictionary.keys())
    shuffle(block_names)

    return block_names, block_dictionary


def run_trial_loop(
    win: pg.Surface,
    subject_number: str,
    block_name: str,
    targets: list[str],
    distractors: list[str],
    save_folder: str,
    audio_engine: AudioEngine,
) -> None:
    """Run the main trial loop for a single block."""
    pg.event.clear()
    trial_number = 0
    max_plays = MAX_PLAYS
    reminder_interval = REMINDER_INTERVAL

    audio_stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')

    if block_name == 'full_sentence':
        prefix_wav = os.path.join(audio_stimuli_dir, 'fullsentenceminuswall.wav')
    else:
        prefix_wav = None

    fs_out = int(audio_engine.fs)
    sound, stimulus_number, stimulus_type = _select_stimulus(targets, distractors, prefix_wav, fs_out)

    while targets or distractors:
        play_count = 0
        audio_played = False
        last_audio_start = 0
        audio_duration = 0
        start_ns = None

        # Show periodic reminder if needed (but not on first trial)
        if trial_number > 0 and trial_number % reminder_interval == 0:
            _show_periodic_reminder(win, subject_number, save_folder, trial_number, block_name, audio_engine)

        while True:
            current_time = pg.time.get_ticks()
            time_since_last = current_time - last_audio_start
            audio_still_playing = (last_audio_start != 0) and (time_since_last < audio_duration)
            can_play = (last_audio_start == 0) or (time_since_last >= audio_duration + 250)
            can_respond = audio_played and not audio_still_playing

            button_rect = _draw_audio_interface(
                win,
                play_count,
                max_plays,
                audio_played=audio_played,
                can_play=can_play,
                can_respond=can_respond,
                block_name=block_name
            )
            pg.display.flip()

            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        pg.quit()
                        sys.exit()

                    if can_respond:
                        if start_ns is None:
                            start_ns = time.perf_counter_ns()

                        if event.key == pg.K_y:
                            response_time = (time.perf_counter_ns() - start_ns) / 1_000_000
                            _record_response(subject_number, block_name, stimulus_number, stimulus_type, 'target', response_time, save_folder, play_count)
                            trial_number += 1

                            if targets or distractors:
                                sound, stimulus_number, stimulus_type = _select_stimulus(targets, distractors, prefix_wav, fs_out)
                            break

                        elif event.key == pg.K_n:
                            response_time = (time.perf_counter_ns() - start_ns) / 1_000_000
                            _record_response(subject_number, block_name, stimulus_number, stimulus_type, 'distractor', response_time, save_folder, play_count)
                            trial_number += 1

                            if targets or distractors:
                                sound, stimulus_number, stimulus_type = _select_stimulus(targets, distractors, prefix_wav, fs_out)
                            break

                elif event.type == pg.MOUSEBUTTONDOWN:
                    mouse_pos = pg.mouse.get_pos()
                    if button_rect.collidepoint(mouse_pos) and play_count < max_plays and can_play:
                        audio_duration = _play_audio_stimulus(audio_engine, sound)
                        last_audio_start = pg.time.get_ticks()
                        play_count += 1
                        audio_played = True
                        if start_ns is None:
                            start_ns = time.perf_counter_ns()
            else:
                continue
            break


def run_blocks(
    win: pg.Surface,
    subject_number: str,
    save_folder: str,
    audio_engine: AudioEngine,
    sleepiness_responses: list | None = None,
    stanford_sleepiness_scale_func=None,
) -> list[str]:
    """Run all experimental blocks."""
    block_names, block_dictionary = prepare_blocks()
    familiarization_session_count = 0

    for i, block_name in enumerate(block_names):
        targets, distractors = block_dictionary[block_name]
        targets = list(targets)
        distractors = list(distractors)

        # Show block instructions and examples
        _show_block_instructions(win, block_name, audio_engine, save_folder, subject_number)

        # Pre-trial screen
        _show_pre_trial_screen(win, block_name)

        # Sleepiness scale before block if function provided
        if stanford_sleepiness_scale_func and sleepiness_responses is not None:
            response = stanford_sleepiness_scale_func(subject_number, win)
            sleepiness_responses.append({'block': i, 'timing': 'pre', 'response': response})

        # Target familiarization before trials
        familiarization_session_count += 1
        _show_target_familiarization(win, subject_number, save_folder, familiarization_session_count, block_name, audio_engine)

        # Run trials
        run_trial_loop(win, subject_number, block_name, targets, distractors, save_folder, audio_engine)

        # Self-reflection after block
        _save_self_reflection(win, subject_number, save_folder, block_name)

        # Sleepiness scale after block if function provided
        if stanford_sleepiness_scale_func and sleepiness_responses is not None:
            response = stanford_sleepiness_scale_func(subject_number, win)
            sleepiness_responses.append({'block': i, 'timing': 'post', 'response': response})

        # Break screen between blocks (not after last block)
        if i < len(block_names) - 1:
            _show_break_screen(win, i)

    return block_names
