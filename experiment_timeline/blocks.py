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
import numpy as np
from random import shuffle, choice
from experiment_helpers.experimenterLevers import NUM_STIMULI_TO_SHOW
import pygame as pg


# Add parent directory for imports
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE_DIR)
sys.path.insert(0, os.path.join(_BASE_DIR, 'experiment_helpers'))
sys.path.insert(0, os.path.join(_BASE_DIR, 'utils'))

from utils.displayEngine import (
    Screen, TextRenderer, TextInput, Button, ButtonStyle,
    Colors, Color, TextStyle, TextAlign, InputMode,
)
from utils.audioEngine import AudioEngine, get_pcm16_mono, concatenate_wavs
from utils.eventLogger import ScreenEventLogger
from experiment_helpers.experimenterLevers import MAX_PLAYS, REMINDER_INTERVAL, FAMILIARIZATION_PLAYS, REMINDER_PLAYS
from experiment_helpers.text_blocks.experimentTextBlocks import (
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
# Audio loading, resampling, caching, and concatenation are provided by
# utils.audioEngine (get_pcm16_mono, concatenate_wavs).  Only the thin
# play helper remains here for convenience.


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
        sound = concatenate_wavs(prefix_wav, stimulus, add_gap=False, fs_out=fs_out)
    else:
        sound = get_pcm16_mono(stimulus, fs_out)

    filename = os.path.splitext(os.path.basename(stimulus))[0]
    return sound, filename, stimulus_type


def _record_response(
    subject_number: str,
    block: str,
    stimulus_number: str,
    stimulus_type: str,
    response: str,
    timestamps: dict,
    save_folder: str,
    play_count: int = 1,
) -> None:
    """Record a trial response."""
    # Save to block subfolder
    block_subfolder = os.path.join(save_folder, block)
    os.makedirs(block_subfolder, exist_ok=True)
    filepath = os.path.join(block_subfolder, f'{block}_{subject_number}.csv')

    header = ['Subject Number', 'Block Scheme', 'Stimulus Number', 'Stimulus Type', 
              'Subject Response','Play Count', 'Trial Start Timestamp', 'Play Button Clicked Timestamp',
              'Audio Start Timestamp', 'Audio End Timestamp', 'Subject Response Timestamp']
    data = [subject_number, block, stimulus_number, stimulus_type, response, play_count, 
            f'{timestamps["Trial Start Timestamp"]}', 
            f'{timestamps["Play Button Clicked Timestamp"]}',
            f'{timestamps["Audio Start Timestamp"]}', 
            f'{timestamps["Audio End Timestamp"]}', 
            f'{timestamps["Subject Response Timestamp"]}'
            ]

    file_exists = os.path.exists(filepath)
    with open(filepath, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(data)


# =============================================================================
# DISPLAY UTILITIES
# =============================================================================

def _show_text_page(
    win: pg.Surface,
    text: str,
    wait_key: int = pg.K_SPACE,
    save_folder: str | None = None,
    subject_number: str | None = None,
    screen_name: str | None = None,
) -> None:
    """Display a page of text and wait for a key press."""
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    # Event logging (optional)
    screen_logger = None
    if save_folder and subject_number and screen_name:
        screen_logger = ScreenEventLogger(screen_name, save_folder, subject_number)

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
            max_width=screen.abs_x(0.92),
            style=style,
            auto_fit=True,
            rel_max_y=0.95,
        )

        screen.update()

        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()
                elif event.key == wait_key:
                    if screen_logger:
                        key_name = pg.key.name(wait_key)
                        screen_logger.log_event('key_press', key_name)
                        screen_logger.save()
                    return


def _show_instructions_(win: pg.Surface, instructions: list[str], max_rel_y: float = 0.70, text_align: str = "LEFT", font_divisor: float = 18) -> int:
    """Draw centered instructions and return the y position after the last line.
    
    Joins the list into a single string (empty strings become blank lines)
    and uses draw_paragraph with auto_fit so the text shrinks to fit.
    """
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    # Join list into single string preserving blank-line paragraph breaks
    text = "\n".join(instructions)
    
    if text_align == "CENTER":
        align = TextAlign.CENTER
    elif text_align == "RIGHT":
        align = TextAlign.RIGHT
    else:
        align = TextAlign.LEFT

    style = TextStyle(
        font_size=screen.scaled_font_size(font_divisor),
        color=Colors.BLACK,
        align=align,
    )
    
    y_after = text_renderer.draw_paragraph(
        text,
        rel_x=0.03,
        rel_y=0.03,
        rel_max_width=0.94,
        style=style,
        auto_fit=True,
        rel_max_y=max_rel_y,
    )
    
    return y_after


def _draw_button_rect(
    win: pg.Surface,
    rect: pg.Rect,
    base_color: Color,
    text_str: str,
    text_color: Color,
    font: pg.font.Font,
    border_width: int = 3,
    is_playing: bool = False,
    hover_enabled: bool = True,
) -> None:
    """Draw a rectangle button.

    * Darkens by 0.6 while ``is_playing`` is True.
    * Darkens by 0.85 when the mouse hovers over the button (if hover_enabled).
    """
    mouse = pg.mouse.get_pos()
    hovered = hover_enabled and rect.collidepoint(mouse)

    if is_playing:
        color = base_color.darken(0.6)
    elif hovered:
        color = base_color.darken(0.85)
    else:
        color = base_color
    pg.draw.rect(win, color.to_tuple(), rect)
    pg.draw.rect(win, Colors.BLACK.to_tuple(), rect, border_width)
    text_surface = font.render(text_str, True, text_color.to_tuple())
    win.blit(text_surface, text_surface.get_rect(center=rect.center))


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
    audio_still_playing: bool = False,
) -> pg.Rect:
    """Draw the audio interface with instructions and play button."""
    screen = Screen(win)
    
    screen.fill()

    # Get block-specific instructions
    if block_name == 'imagined_sentence':
        instructions = list(trialInstructions_imagined_sentence)
    else:
        instructions = list(trialInstructions_full_sentence)

    # Draw instructions using auto-fit so they never overlap
    y_pos = _show_instructions_(win, instructions, max_rel_y=0.50, text_align="LEFT", font_divisor=22)

    # Create play button in remaining space
    button_width = screen.abs_x(0.18)
    button_height = screen.abs_y(0.10)
    button_x = (screen.width - button_width) // 2
    remaining_h = screen.height - y_pos - screen.abs_y(0.05)
    button_y = y_pos + int(remaining_h * 0.3)
    button_rect = pg.Rect(button_x, button_y, button_width, button_height)

    # Determine button state
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

    font = pg.font.SysFont("times new roman", max(18, screen.height // 35))
    _draw_button_rect(win, button_rect, color, "Play Audio", text_color, font, hover_enabled=enabled and not audio_still_playing)

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
    
    # Event logging
    screen_logger = ScreenEventLogger(f'pre_examples_familiarization_{block_name}', save_folder, subject_number)
    
    # Load target sound
    audio_stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')
    actual_target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    fs_out = int(audio_engine.fs)
    actual_target_pcm = get_pcm16_mono(actual_target_path, fs_out)

    required_plays = FAMILIARIZATION_PLAYS
    play_count = 0
    last_audio_start = 0
    audio_duration = int(round(1000.0 * (actual_target_pcm.shape[0] / fs_out)))

    # Get instructions based on block
    if block_name == "full_sentence":
        instructions = [s.format(required_plays=required_plays) for s in preExamplesFamiliarizationInstructions_full_sentence]
    else:
        instructions = [s.format(required_plays=required_plays) for s in preExamplesFamiliarizationInstructions_imagined_sentence]

    while True:
        screen.fill()
        current_time = pg.time.get_ticks()
        time_since_last = current_time - last_audio_start
        can_play = (last_audio_start == 0) or (time_since_last >= audio_duration + 250)
        audio_still_playing = (last_audio_start != 0) and (time_since_last < audio_duration)
        continue_enabled = (play_count >= required_plays) and (not audio_still_playing)

        # Draw instructions
        y_pos = _show_instructions_(win, instructions, text_align="LEFT")

        # Position buttons in remaining space below text
        remaining_h = screen.height - y_pos - screen.abs_y(0.05)
        btn_width = screen.abs_x(0.2)
        btn_height = min(screen.abs_y(0.08), int(remaining_h * 0.3))
        cont_width = screen.abs_x(0.15)
        cont_height = min(screen.abs_y(0.06), int(remaining_h * 0.25))
        gap = min(20, int(remaining_h * 0.1))

        play_y = y_pos + int(remaining_h * 0.25) - btn_height // 2
        cont_y = play_y + btn_height + gap

        play_rect = pg.Rect((screen.width - btn_width) // 2, play_y, btn_width, btn_height)
        cont_rect = pg.Rect((screen.width - cont_width) // 2, cont_y, cont_width, cont_height)

        # Draw play button
        play_enabled = can_play and play_count < required_plays * 10
        if play_enabled:
            play_color = Colors.BLUE
            play_text_color = Colors.WHITE
        else:
            play_color = Colors.GRAY
            play_text_color = Colors.BLACK

        # Draw continue button
        cont_color = Colors.GREEN if continue_enabled else Colors.GRAY

        # Button text
        font = pg.font.SysFont("times new roman", max(16, screen.height // 40))
        _draw_button_rect(win, play_rect, play_color, "Play Sentence", play_text_color, font, hover_enabled=play_enabled and not audio_still_playing)
        _draw_button_rect(win, cont_rect, cont_color, "Continue", Colors.BLACK, font, hover_enabled=continue_enabled and not audio_still_playing)

        screen.update()

        for event in pg.event.get():
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                pg.quit()
                sys.exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                mouse = pg.mouse.get_pos()
                if play_rect.collidepoint(mouse) and can_play:
                    screen_logger.log_event('button_click', 'play_sentence')
                    audio_duration = _play_audio_stimulus(audio_engine, actual_target_pcm)
                    last_audio_start = current_time
                    play_count += 1
                elif cont_rect.collidepoint(mouse) and continue_enabled:
                    screen_logger.log_event('button_click', 'continue')
                    screen_logger.save()
                    # Save play count data
                    _save_pre_examples_familiarization_data(subject_number, save_folder, play_count, block_name)
                    return


def _save_pre_examples_familiarization_data(
    subject_number: str,
    save_folder: str,
    play_count: int,
    block_name: str,
) -> None:
    """Save pre-examples familiarization play count data."""
    from datetime import datetime
    
    # Save to block subfolder
    block_subfolder = os.path.join(save_folder, block_name)
    os.makedirs(block_subfolder, exist_ok=True)
    filepath = os.path.join(block_subfolder, f'pre_examples_familiarization_{block_name}_{subject_number}.csv')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = ['subject_number', 'block_name', 'play_count', 'timestamp']
    data = [subject_number, block_name, play_count, timestamp]

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerow(data)


def _show_block_examples(
    win: pg.Surface,
    audio_engine: AudioEngine,
    block_name: str,
    save_folder: str,
    subject_number: str,
) -> None:
    """Show the block examples screen with target and distractor samples.

    Matches the original showBlockExamples layout:
    - Instruction text at top (auto-fit)
    - Horizontal row: target ("Wall") buttons
    - Centre: "Actual Audio" button
    - Horizontal row: distractor ("No Wall") buttons
    - "Continue" button (active after sequential guided listening)

    Phases:
        0 → user must click Actual Audio
        1 → user steps through each target in order
        2 → user clicks Actual Audio again
        3 → user steps through each distractor in order
        4 → all buttons unlocked, user can replay freely
    """
    pg.mouse.set_visible(True)
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    current_w, current_h = screen.width, screen.height
    
    # Event logging
    screen_logger = ScreenEventLogger(f'examples_screen_{block_name}', save_folder, subject_number)

    # Instruction text
    if block_name == "imagined_sentence":
        instruction_text = blockExamplesInstructions_imagined_sentence
    else:
        instruction_text = blockExamplesInstructions_full_sentence

    # Load example files
    audio_stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')
    examples_targets_dir = os.path.join(audio_stimuli_dir, 'examples', 'targets')
    examples_distractors_dir = os.path.join(audio_stimuli_dir, 'examples', 'distractors')

    target_files = sorted([f for f in os.listdir(examples_targets_dir) if f.lower().endswith('.wav')])
    distractor_files = sorted([f for f in os.listdir(examples_distractors_dir) if f.lower().endswith('.wav')])

    fs_out = int(audio_engine.fs)

    # Load actual audio — differs by block
    if block_name == 'imagined_sentence':
        actual_target_path = os.path.join(audio_stimuli_dir, 'wall.wav')
    else:
        actual_target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    actual_pcm = get_pcm16_mono(actual_target_path, fs_out)

    # Load example audio — full_sentence block concatenates prefix
    if block_name == 'full_sentence':
        prefix_path = os.path.join(audio_stimuli_dir, 'fullsentenceminuswall.wav')
        targets_pcm = [
            concatenate_wavs(prefix_path, os.path.join(examples_targets_dir, f), add_gap=False, fs_out=fs_out)
            for f in target_files
        ]
        distractors_pcm = [
            concatenate_wavs(prefix_path, os.path.join(examples_distractors_dir, f), add_gap=False, fs_out=fs_out)
            for f in distractor_files
        ]
    else:
        targets_pcm = [get_pcm16_mono(os.path.join(examples_targets_dir, f), fs_out) for f in target_files]
        distractors_pcm = [get_pcm16_mono(os.path.join(examples_distractors_dir, f), fs_out) for f in distractor_files]

    # Play-count tracking
    target_counts = [0] * len(target_files)
    distractor_counts = [0] * len(distractor_files)
    actual_count = 0
    last_audio_start = 0
    audio_duration = 0

    # Phase system for guided sequential listening
    phase = 0
    next_target_idx = 0
    next_distractor_idx = 0
    last_played_type: str | None = None   # 'actual' | 'target' | 'distractor'
    last_played_index: int | None = None

    # ── grid helper (computed once, doesn't change) ──
    margin_x = int(0.06 * current_w)
    min_spacing = int(0.02 * current_w)
    min_btn_w = int(0.10 * current_w)
    row_gap = int(0.02 * current_h)
    
    # Smaller buttons for imagined_sentence to allow more text space
    if block_name == 'imagined_sentence':
        grid_btn_h = max(30, int(0.045 * current_h))
        actual_btn_h = max(30, int(0.045 * current_h))
        text_max_y = 0.50  # More room for text
    else:
        grid_btn_h = max(32, int(0.055 * current_h))
        actual_btn_h = max(32, int(0.055 * current_h))
        text_max_y = 0.45

    def _compute_grid(count: int, top_y: int):
        if count <= 0:
            return [], top_y
        cols = min(6, count)
        while cols > 1:
            avail = current_w - 2 * margin_x - (cols - 1) * min_spacing
            if avail / cols >= min_btn_w:
                break
            cols -= 1
        avail = current_w - 2 * margin_x - (cols - 1) * min_spacing
        btn_w = max(min_btn_w, int(avail // cols))
        spacing = 0 if cols == 1 else int((current_w - 2 * margin_x - cols * btn_w) / (cols - 1))
        btn_h = grid_btn_h  # Use configured button height
        rows = -((-count) // cols)
        rects: list[pg.Rect] = []
        for idx in range(count):
            r, c = divmod(idx, cols)
            x = margin_x + c * (btn_w + spacing)
            yy = top_y + r * (btn_h + row_gap)
            rects.append(pg.Rect(int(x), int(yy), btn_w, btn_h))
        total_h = rows * btn_h + (rows - 1) * row_gap
        return rects, top_y + total_h

    while True:
        screen.fill()
        current_time = pg.time.get_ticks()
        time_since_last = current_time - last_audio_start
        audio_still_playing = (last_audio_start != 0) and (time_since_last < audio_duration)

        # ── instruction text (auto-fit into top area) ──
        instr_style = TextStyle(
            font_size=screen.scaled_font_size(16),
            color=Colors.BLACK,
            align=TextAlign.LEFT,
        )
        y_after_text = text_renderer.draw_paragraph(
            instruction_text,
            rel_x=0.03, rel_y=0.02,
            rel_max_width=0.94,
            style=instr_style,
            auto_fit=True,
            rel_max_y=text_max_y,
        )

        # ── layout ──
        top_y = y_after_text + int(0.06 * current_h)
        label_font = pg.font.SysFont('times new roman', max(20, current_h // 36), bold=True)

        # "Wall" label (bold)
        t_lab = label_font.render('Wall', True, Colors.BLACK.to_tuple())
        win.blit(t_lab, (margin_x, top_y))
        top_y += t_lab.get_height() + 8

        target_rects, next_y = _compute_grid(len(target_files), top_y)

        # Actual Audio button (centred)
        actual_w = int(0.28 * current_w)
        actual_h = actual_btn_h  # Use configured height
        actual_rect = pg.Rect((current_w - actual_w) // 2, next_y + int(0.03 * current_h), actual_w, actual_h)

        # "No Wall" label (bold)
        d_label_y = actual_rect.bottom + int(0.04 * current_h)
        d_lab = label_font.render('No Wall', True, Colors.BLACK.to_tuple())
        win.blit(d_lab, (margin_x, d_label_y))

        distractor_rects, next_y = _compute_grid(len(distractor_files), d_label_y + d_lab.get_height() + 8)

        # Continue button
        continue_w = int(0.18 * current_w)
        continue_h = int(0.05 * current_h)
        continue_rect = pg.Rect((current_w - continue_w) // 2, next_y + int(0.03 * current_h), continue_w, continue_h)

        btn_font = pg.font.SysFont('times new roman', max(14, current_h // 44))

        # ── draw helper (darken when playing, hover darken, gray when disabled) ──
        def _draw_btn(rect: pg.Rect, label: str, enabled: bool, is_playing: bool = False):
            mouse_pos = pg.mouse.get_pos()
            # Disable hover effect for all buttons when any audio is playing
            hovered = rect.collidepoint(mouse_pos) and enabled and not audio_still_playing
            if enabled:
                text_col = Colors.WHITE
                if 'No Wall' in label:
                    base = Colors.RED
                elif 'Actual' in label:
                    base = Colors.BLUE
                else:
                    base = Colors.GREEN
                    text_col = Colors.BLACK
                if is_playing:
                    col = base.darken(0.6)
                elif hovered:
                    col = base.darken(0.85)
                else:
                    col = base
            else:
                col = Colors.GRAY
                text_col = Colors.BLACK
            pg.draw.rect(win, col.to_tuple(), rect)
            pg.draw.rect(win, Colors.BLACK.to_tuple(), rect, 2)
            s = btn_font.render(label, True, text_col.to_tuple())
            win.blit(s, s.get_rect(center=rect.center))

        unlocked = phase >= 4
        can_click_actual = phase in (0, 2)
        can_click_targets = phase == 1
        can_click_distractors = phase == 3

        # Draw target buttons
        for i, rect in enumerate(target_rects):
            if unlocked:
                en = True
                playing = last_played_type == 'target' and last_played_index == i and audio_still_playing
            else:
                en = can_click_targets and i == next_target_idx and not audio_still_playing
                playing = last_played_type == 'target' and last_played_index == i and audio_still_playing
            _draw_btn(rect, f'Wall {i+1}', en, playing)

        # Draw actual button
        if unlocked:
            act_en = True
            act_playing = last_played_type == 'actual' and audio_still_playing
        else:
            act_en = can_click_actual and not audio_still_playing
            act_playing = last_played_type == 'actual' and audio_still_playing
        _draw_btn(actual_rect, 'Actual Audio', act_en, act_playing)

        # Draw distractor buttons
        for i, rect in enumerate(distractor_rects):
            if unlocked:
                en = True
                playing = last_played_type == 'distractor' and last_played_index == i and audio_still_playing
            else:
                en = can_click_distractors and i == next_distractor_idx and not audio_still_playing
                playing = last_played_type == 'distractor' and last_played_index == i and audio_still_playing
            _draw_btn(rect, f'No Wall {i+1}', en, playing)

        # Continue button — only active after phase 4 and nothing playing
        cont_enabled = unlocked and not audio_still_playing
        mouse_pos = pg.mouse.get_pos()
        # White, no hover when audio playing
        if cont_enabled:
            cont_col = Colors.LIGHT_GRAY if (continue_rect.collidepoint(mouse_pos) and not audio_still_playing) else Colors.WHITE
        else:
            cont_col = Colors.GRAY
        pg.draw.rect(win, cont_col.to_tuple(), continue_rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), continue_rect, 2)
        cont_font = pg.font.SysFont('times new roman', max(16, current_h // 38))
        cont_surf = cont_font.render('Continue', True, Colors.BLACK.to_tuple())
        win.blit(cont_surf, cont_surf.get_rect(center=continue_rect.center))

        screen.update()

        # ── event handling ──
        for event in pg.event.get():
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                pg.quit()
                sys.exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                mouse = pg.mouse.get_pos()
                ct = pg.time.get_ticks()
                ts = ct - last_audio_start
                still_playing = (last_audio_start != 0) and (ts < audio_duration)

                # Continue
                if continue_rect.collidepoint(mouse) and cont_enabled:
                    screen_logger.log_event('button_click', 'continue')
                    screen_logger.save()
                    # Save to block subfolder
                    block_subfolder = os.path.join(save_folder, block_name)
                    os.makedirs(block_subfolder, exist_ok=True)
                    out_path = os.path.join(block_subfolder, f'example_play_counts_{block_name}_{subject_number}.csv')
                    with open(out_path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        # Header row: 1-indexed column names
                        writer.writerow(['actual_audio'] + [f'target_{i+1}' for i in range(len(target_files))] +
                                       [f'distractor_{i+1}' for i in range(len(distractor_files))])
                        # Play counts row
                        writer.writerow([actual_count] + target_counts + distractor_counts)
                        # Filename row (without .wav extension)
                        actual_name = os.path.splitext(os.path.basename(actual_target_path))[0]
                        target_names = [os.path.splitext(f)[0] for f in target_files]
                        distractor_names = [os.path.splitext(f)[0] for f in distractor_files]
                        writer.writerow([actual_name] + target_names + distractor_names)
                    return

                if still_playing:
                    continue

                # Actual Audio
                if actual_rect.collidepoint(mouse) and (unlocked or can_click_actual):
                    screen_logger.log_event('button_click', 'actual_audio')
                    audio_duration = _play_audio_stimulus(audio_engine, actual_pcm)
                    last_audio_start = ct
                    last_played_type = 'actual'
                    last_played_index = None
                    actual_count += 1
                    if phase == 0:
                        phase = 1
                    elif phase == 2:
                        phase = 3
                    continue

                # Targets
                for i, rect in enumerate(target_rects):
                    if rect.collidepoint(mouse) and (unlocked or (can_click_targets and i == next_target_idx)):
                        screen_logger.log_event('button_click', f'target_{i}')
                        audio_duration = _play_audio_stimulus(audio_engine, targets_pcm[i])
                        last_audio_start = ct
                        last_played_type = 'target'
                        last_played_index = i
                        target_counts[i] += 1
                        if phase == 1 and i == next_target_idx:
                            next_target_idx += 1
                            if next_target_idx >= len(target_files):
                                phase = 2
                        break
                else:
                    # Distractors
                    for i, rect in enumerate(distractor_rects):
                        if rect.collidepoint(mouse) and (unlocked or (can_click_distractors and i == next_distractor_idx)):
                            screen_logger.log_event('button_click', f'distractor_{i}')
                            audio_duration = _play_audio_stimulus(audio_engine, distractors_pcm[i])
                            last_audio_start = ct
                            last_played_type = 'distractor'
                            last_played_index = i
                            distractor_counts[i] += 1
                            if phase == 3 and i == next_distractor_idx:
                                next_distractor_idx += 1
                                if next_distractor_idx >= len(distractor_files):
                                    phase = 4
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
    
    # Event logging
    screen_logger = ScreenEventLogger(f'target_familiarization_{block_name}_{session_number}', save_folder, subject_number)

    # Load target sound
    audio_stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')
    actual_target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    fs_out = int(audio_engine.fs)
    actual_target_pcm = get_pcm16_mono(actual_target_path, fs_out)

    required_plays = FAMILIARIZATION_PLAYS
    play_count = 0
    last_audio_start = 0
    audio_duration = int(round(1000.0 * (actual_target_pcm.shape[0] / fs_out)))

    if block_name == "full_sentence":
        instructions = [s.format(required_plays=required_plays) for s in targetFamiliarizationInstructions_full_sentence]
    else:
        instructions = [s.format(required_plays=required_plays) for s in targetFamiliarizationInstructions_imagined_sentence]

    while True:
        screen.fill()
        current_time = pg.time.get_ticks()
        time_since_last = current_time - last_audio_start
        can_play = (last_audio_start == 0) or (time_since_last >= audio_duration + 350)
        audio_still_playing = (last_audio_start != 0) and (time_since_last < audio_duration)
        continue_enabled = (play_count >= required_plays) and (not audio_still_playing)

        y_pos = _show_instructions_(win, instructions, text_align="LEFT")

        # Dynamic button placement in remaining space
        remaining_h = screen.height - y_pos - screen.abs_y(0.05)
        play_y = y_pos + int(remaining_h * 0.20)
        btn_width = screen.abs_x(0.22)
        btn_height = max(40, int(remaining_h * 0.22))
        cont_y = play_y + btn_height + int(remaining_h * 0.10)
        cont_width = screen.abs_x(0.17)
        cont_height = max(36, int(remaining_h * 0.18))

        play_rect = pg.Rect((screen.width - btn_width) // 2, play_y, btn_width, btn_height)
        cont_rect = pg.Rect((screen.width - cont_width) // 2, cont_y, cont_width, cont_height)

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

        cont_color = Colors.GREEN if continue_enabled else Colors.GRAY

        font = pg.font.SysFont("times new roman", max(16, screen.height // 40))
        play_text_str = "Max Plays Reached" if play_count >= required_plays else "Play Sentence"
        _draw_button_rect(win, play_rect, play_color, play_text_str, play_text_color, font, hover_enabled=can_click_play and not audio_still_playing)
        _draw_button_rect(win, cont_rect, cont_color, "Continue", Colors.BLACK, font, hover_enabled=continue_enabled and not audio_still_playing)

        screen.update()

        for event in pg.event.get():
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                pg.quit()
                sys.exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                mouse = pg.mouse.get_pos()
                if play_rect.collidepoint(mouse) and can_click_play:
                    screen_logger.log_event('button_click', 'play_sentence')
                    audio_duration = _play_audio_stimulus(audio_engine, actual_target_pcm)
                    last_audio_start = current_time
                    play_count += 1
                elif cont_rect.collidepoint(mouse) and continue_enabled:
                    screen_logger.log_event('button_click', 'continue')
                    screen_logger.save()
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
    """Save target familiarization data to a block-specific file."""
    from datetime import datetime
    
    # Save to block subfolder
    block_subfolder = os.path.join(save_folder, block_name)
    os.makedirs(block_subfolder, exist_ok=True)
    filepath = os.path.join(block_subfolder, f'target_familiarization_{block_name}_{subject_number}.csv')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = ['subject_number', 'session_number', 'block_name', 'play_count', 'timestamp']
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
    
    # Event logging
    screen_logger = ScreenEventLogger(f'periodic_reminder_{block_name}_trial{trial_number}', save_folder, subject_number)

    audio_stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')
    actual_target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    fs_out = int(audio_engine.fs)
    actual_target_pcm = get_pcm16_mono(actual_target_path, fs_out)

    required_plays = REMINDER_PLAYS
    play_count = 0
    last_audio_start = 0
    audio_duration = int(round(1000.0 * (actual_target_pcm.shape[0] / fs_out)))

    if block_name == "full_sentence":
        instructions = [s.format(required_plays=required_plays) for s in periodicReminderInstructions_full_sentence]
    else:
        instructions = [s.format(required_plays=required_plays) for s in periodicReminderInstructions_imagined_sentence]

    while True:
        screen.fill()
        current_time = pg.time.get_ticks()
        time_since_last = current_time - last_audio_start
        can_play = (last_audio_start == 0) or (time_since_last >= audio_duration + 350)
        audio_still_playing = (last_audio_start != 0) and (time_since_last < audio_duration)
        continue_enabled = (play_count >= required_plays) and (not audio_still_playing)

        y_pos = _show_instructions_(win, instructions, text_align="LEFT", font_divisor=20)

        # Dynamic button placement in remaining space
        remaining_h = screen.height - y_pos - screen.abs_y(0.05)
        play_y = y_pos + int(remaining_h * 0.25)
        btn_width = screen.abs_x(0.22)
        btn_height = max(40, int(remaining_h * 0.25))
        cont_y = play_y + btn_height + int(remaining_h * 0.12)
        cont_width = screen.abs_x(0.15)
        cont_height = max(26, int(remaining_h * 0.15))

        play_rect = pg.Rect((screen.width - btn_width) // 2, play_y, btn_width, btn_height)
        cont_rect = pg.Rect((screen.width - cont_width) // 2, cont_y, cont_width, cont_height)

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

        cont_color = Colors.GREEN if continue_enabled else Colors.GRAY

        font = pg.font.SysFont("times new roman", max(16, screen.height // 40))
        play_text_str = "Max Plays Reached" if play_count >= required_plays else "Play Sentence"
        _draw_button_rect(win, play_rect, play_color, play_text_str, play_text_color, font, hover_enabled=can_click and not audio_still_playing)
        _draw_button_rect(win, cont_rect, cont_color, "Continue", Colors.BLACK, font, hover_enabled=continue_enabled and not audio_still_playing)

        screen.update()

        for event in pg.event.get():
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                pg.quit()
                sys.exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                mouse = pg.mouse.get_pos()
                if play_rect.collidepoint(mouse) and can_click:
                    screen_logger.log_event('button_click', 'play_sentence')
                    audio_duration = _play_audio_stimulus(audio_engine, actual_target_pcm)
                    last_audio_start = current_time
                    play_count += 1
                elif cont_rect.collidepoint(mouse) and continue_enabled:
                    screen_logger.log_event('button_click', 'continue')
                    screen_logger.save()
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

    # Save to block subfolder
    block_subfolder = os.path.join(save_folder, block_name)
    os.makedirs(block_subfolder, exist_ok=True)
    filepath = os.path.join(block_subfolder, f'periodic_reminders_{block_name}_{subject_number}.csv')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = ['subject_number', 'block_name', 'trial_number', 'play_count', 'timestamp']
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

def _get_subject_input(win: pg.Surface, prompt: str, screen_logger: ScreenEventLogger | None = None, input_name: str = "") -> str:
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
    if screen_logger and result and input_name:
        screen_logger.log_event('text_submitted', input_name)
    return result if result else ""


def _save_self_reflection(
    win: pg.Surface,
    subject_number: str,
    save_folder: str,
    block_name: str
) -> None:
    """Collect and save self-reflection responses after a block."""
    # Event logging
    screen_logger = ScreenEventLogger(f'self_reflection_{block_name}', save_folder, subject_number)
    
    explanation = _get_subject_input(
        win,
        'During the previous block, how did you decide whether or not the word "Wall" was in each of the stimuli? What were you thinking about or considering as you made that decision?\n\n**Response**',
        screen_logger, 'methodology_explanation'
    )
    
    changes = _get_subject_input(
        win,
        'Did your methodology change or evolve over the course of the previous block?\n\n**Response**',
        screen_logger, 'methodology_changes'
    )

    if block_name == 'imagined_sentence':
        rule_following = _get_subject_input(
            win,
            'During this block did you imagine the sentence before playing the stimuli and then click "Play Audio" at the moment you would have imagined the word "Wall"?\n  - Please begin your response with either "Yes." or "No."\n  - You may include additional information after typing "Yes." or "No."\n\n**Response**',
            screen_logger, 'imagination_rule_following'
        )
    else:
        rule_following = 'N/A'

    screen_logger.save()
    
    # Save each response as a separate .txt file in block subfolder
    block_subfolder = os.path.join(save_folder, block_name)
    os.makedirs(block_subfolder, exist_ok=True)
    
    explanation_path = os.path.join(block_subfolder, f'self_reflection_methodology_explanation_{block_name}_{subject_number}.txt')
    with open(explanation_path, 'w') as f:
        f.write(explanation or '')
    
    changes_path = os.path.join(block_subfolder, f'self_reflection_methodology_changes_{block_name}_{subject_number}.txt')
    with open(changes_path, 'w') as f:
        f.write(changes or '')
    
    if block_name == 'imagined_sentence':
        rule_path = os.path.join(block_subfolder, f'self_reflection_imagination_rule_following_{block_name}_{subject_number}.txt')
        with open(rule_path, 'w') as f:
            f.write(rule_following or '')


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

    _show_text_page(win, text, wait_key=pg.K_SPACE,
                   save_folder=save_folder, subject_number=subject_number,
                   screen_name=f'block_instructions_{block_name}')
    _show_pre_examples_familiarization(win, subject_number, save_folder, block_name, audio_engine)
    _show_block_examples(win, audio_engine, block_name, save_folder, subject_number)
    pg.mouse.set_visible(False)


def _show_pre_trial_screen(win: pg.Surface, block_name: str, save_folder: str, subject_number: str) -> None:
    """Show pre-trial quick response screen."""
    if block_name == "full_sentence":
        text = preTrialQuickResponseTextFullSentence
    else:
        text = preTrialQuickResponseTextImaginedSentence
    
    _show_text_page(win, text, wait_key=pg.K_SPACE,
                   save_folder=save_folder, subject_number=subject_number,
                   screen_name=f'pre_trial_{block_name}')


def _show_break_screen(win: pg.Surface, block_index: int, save_folder: str, subject_number: str) -> None:
    """Show break screen between blocks."""
    _show_text_page(win, breakScreenText, wait_key=pg.K_f,
                   save_folder=save_folder, subject_number=subject_number,
                   screen_name=f'break_screen_{block_index}')


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
    num_stimuli: int,
    save_folder: str,
    audio_engine: AudioEngine,
) -> None:
    """Run the main trial loop for a single block."""
    pg.event.clear()
    trial_number = 1
    max_plays = MAX_PLAYS
    reminder_interval = REMINDER_INTERVAL
    total_trials = num_stimuli if NUM_STIMULI_TO_SHOW == -1 else min(num_stimuli, NUM_STIMULI_TO_SHOW)

    audio_stimuli_dir = os.path.join(_BASE_DIR, 'audio_stimuli')

    if block_name == 'full_sentence':
        prefix_wav = os.path.join(audio_stimuli_dir, 'fullsentenceminuswall.wav')
    else:
        prefix_wav = None

    fs_out = int(audio_engine.fs)
    sound, stimulus_number, stimulus_type = _select_stimulus(targets, distractors, prefix_wav, fs_out)

    while (targets or distractors) and (trial_number <= NUM_STIMULI_TO_SHOW or NUM_STIMULI_TO_SHOW == -1):
        
        # Per-trial timestamps dictionary
        timestamps = {}
        timestamps['Trial Start Timestamp'] = time.perf_counter_ns()

        play_count = 0
        audio_played = False
        last_audio_start = 0
        audio_duration = 0
        start_ns = None


        while True:
            current_time = pg.time.get_ticks()
            time_since_last = current_time - last_audio_start
            audio_still_playing = (last_audio_start != 0) and (time_since_last < audio_duration)
            can_play = (last_audio_start == 0) or (time_since_last >= audio_duration + 150)
            can_respond = audio_played and not audio_still_playing

            button_rect = _draw_audio_interface(
                win,
                play_count,
                max_plays,
                audio_played=audio_played,
                can_play=can_play,
                can_respond=can_respond,
                block_name=block_name,
                audio_still_playing=audio_still_playing,
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
                            # record subject response timestamp (perf ns)
                            timestamps['Subject Response Timestamp'] = time.perf_counter_ns()
                            _record_response(subject_number, block_name, stimulus_number, stimulus_type, 'target', timestamps, save_folder, play_count)
                            trial_number += 1

                            if targets or distractors:
                                sound, stimulus_number, stimulus_type = _select_stimulus(targets, distractors, prefix_wav, fs_out)
                            break

                        elif event.key == pg.K_n:
                            timestamps['Subject Response Timestamp'] = time.perf_counter_ns()
                            _record_response(subject_number, block_name, stimulus_number, stimulus_type, 'distractor', timestamps, save_folder, play_count)
                            trial_number += 1

                            if targets or distractors:
                                sound, stimulus_number, stimulus_type = _select_stimulus(targets, distractors, prefix_wav, fs_out)
                            break

                elif event.type == pg.MOUSEBUTTONDOWN:
                    mouse_pos = pg.mouse.get_pos()
                    if button_rect.collidepoint(mouse_pos) and play_count < max_plays and can_play:
                        # Record first time play button clicked for this trial (perf ns)
                        if 'Play Button Clicked Timestamp' not in timestamps:
                            timestamps['Play Button Clicked Timestamp'] = time.perf_counter_ns()

                        # Start audio and record audio start/end timestamps (perf ns)
                        audio_start_perf = time.perf_counter_ns()
                        audio_duration = _play_audio_stimulus(audio_engine, sound)
                        timestamps['Audio Start Timestamp'] = int(audio_start_perf)
                        try:
                            # audio_duration is expected in milliseconds
                            audio_end_perf = audio_start_perf + int(audio_duration) * 1_000_000
                            timestamps['Audio End Timestamp'] = int(audio_end_perf)
                        except Exception:
                            # fallback to current perf time if audio_duration is not numeric
                            timestamps['Audio End Timestamp'] = time.perf_counter_ns()

                        last_audio_start = pg.time.get_ticks()
                        play_count += 1
                        audio_played = True
                        if start_ns is None:
                            start_ns = time.perf_counter_ns()
            else:
                continue
            
            # Show periodic reminder if needed (but not before first or after last trial)
            completed_trial = trial_number - 1
            if (completed_trial % reminder_interval == 0) and (0 < completed_trial < total_trials):
                _show_periodic_reminder(win, subject_number, save_folder, completed_trial, block_name, audio_engine)
            
            break

        # 2-second blank screen pause between trials
        screen = Screen(win)
        screen.fill()
        screen.update()
        pg.time.wait(2000)
        pg.event.clear()


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
        num_stimuli = len(targets) + len(distractors)

        # Show block instructions and examples
        _show_block_instructions(win, block_name, audio_engine, save_folder, subject_number)

        # Pre-trial screen
        _show_pre_trial_screen(win, block_name, save_folder, subject_number)

        # Sleepiness scale before block if function provided
        if stanford_sleepiness_scale_func and sleepiness_responses is not None:
            from datetime import datetime
            response = stanford_sleepiness_scale_func(subject_number, win)
            sleepiness_responses.append({
                'block_index': i + 1,  # 1-indexed
                'block_scheme': block_name,
                'timing': 'pre',
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'response': response
            })

        # Target familiarization before trials
        familiarization_session_count += 1
        _show_target_familiarization(win, subject_number, save_folder, familiarization_session_count, block_name, audio_engine)

        # Run trials
        run_trial_loop(win, subject_number, block_name, targets, distractors, num_stimuli, save_folder, audio_engine)

        # Self-reflection after block
        _save_self_reflection(win, subject_number, save_folder, block_name)

        # Sleepiness scale after block if function provided
        if stanford_sleepiness_scale_func and sleepiness_responses is not None:
            from datetime import datetime
            response = stanford_sleepiness_scale_func(subject_number, win)
            sleepiness_responses.append({
                'block_index': i + 1,  # 1-indexed
                'block_scheme': block_name,
                'timing': 'post',
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'response': response
            })

        # Break screen between blocks (not after last block)
        if i < len(block_names) - 1:
            _show_break_screen(win, i, save_folder, subject_number)

    return block_names
