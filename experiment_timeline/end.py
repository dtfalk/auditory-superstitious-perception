"""
End Subtimeline
===============
Handles experiment completion including:
- Exit screen
- Summary data calculation
- Cleanup

Uses displayEngine for all rendering - no dependency on helperFunctions.py
"""

import os
import sys
import csv
import pygame as pg
from scipy.stats import norm

# Add parent directory for imports
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE_DIR)
sys.path.insert(0, os.path.join(_BASE_DIR, 'experiment_helpers'))
sys.path.insert(0, os.path.join(_BASE_DIR, 'utils'))

from utils.displayEngine import (
    Screen, TextRenderer, TextInput,
    Colors, TextStyle, TextAlign, InputMode,
)
from utils.eventLogger import get_global_logger, ScreenEventLogger
from experiment_helpers.text_blocks.experimentTextBlocks import exitScreenText


# =============================================================================
# D-PRIME CALCULATION
# =============================================================================

def _calculate_dprime(hits: int, misses: int, correct_rejections: int, false_alarms: int):
    """Calculate d-prime score with extreme value corrections."""
    try:
        hit_rate = hits / (hits + misses)
        false_alarm_rate = false_alarms / (false_alarms + correct_rejections)
    except ZeroDivisionError:
        return 'NaN'

    # Values for fixing extreme d-primes
    half_hit = 0.5 / (hits + misses) if (hits + misses) > 0 else 0.5
    half_false_alarm = 0.5 / (false_alarms + correct_rejections) if (false_alarms + correct_rejections) > 0 else 0.5

    if hit_rate == 1:
        hit_rate = 1 - half_hit
    if hit_rate == 0:
        hit_rate = half_hit
    if false_alarm_rate == 1:
        false_alarm_rate = 1 - half_false_alarm
    if false_alarm_rate == 0:
        false_alarm_rate = half_false_alarm

    # Calculate z values
    hit_rate_z = norm.ppf(hit_rate)
    false_alarm_rate_z = norm.ppf(false_alarm_rate)

    # Calculate d-prime
    dprime = hit_rate_z - false_alarm_rate_z
    return dprime


def _write_summary_data(subject_number: str, block_names: list[str], save_folder: str) -> None:
    """Write summary data with d-prime calculations."""
    filepath = os.path.join(save_folder, f'summaryData_{subject_number}.csv')

    # Load data files in correct order
    data_files = [
        os.path.join(save_folder, f'{block}_{subject_number}.csv')
        for block in block_names
    ]

    # Calculate d-primes for each block
    dprimes = []
    for data_file in data_files:
        if not os.path.exists(data_file):
            dprimes.append('NaN')
            continue
            
        with open(data_file, mode='r', newline='') as f:
            reader = csv.reader(f)
            lines = list(reader)
            header = lines[0]
            data = lines[1:]

            # Create index dictionary
            indices = {entry: i for i, entry in enumerate(header)}

            # Collect signal detection data
            hits = 0
            misses = 0
            false_alarms = 0
            correct_rejections = 0

            for entry in data:
                stim_type = entry[indices['Stimulus Type']]
                response = entry[indices['Subject Response']]
                
                if stim_type == 'target' and response == 'target':
                    hits += 1
                elif stim_type == 'target' and response == 'distractor':
                    misses += 1
                elif stim_type == 'distractor' and response == 'target':
                    false_alarms += 1
                else:
                    correct_rejections += 1
            
            dprime = _calculate_dprime(hits, misses, correct_rejections, false_alarms)
            dprimes.append(dprime)

    # Write summary file
    header = ['Subject Number']
    for i, block in enumerate(block_names):
        header.extend([f'Block {i+1}', f'Block {i+1} D-Prime'])
    
    row = [subject_number]
    for i, block in enumerate(block_names):
        row.extend([block, dprimes[i] if i < len(dprimes) else 'NaN'])

    with open(filepath, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerow(row)


# =============================================================================
# EXIT SCREEN
# =============================================================================

def _show_exit_screen(win: pg.Surface, save_folder: str = "", subject_number: str = "") -> None:
    """Display exit screen with thank you message."""
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    # Set up logging if save_folder provided
    logger = None
    if save_folder and subject_number:
        logger = ScreenEventLogger("exit_screen", save_folder, subject_number)
        logger.log_event("screen_presented", "exit_screen")
    
    style = TextStyle(
        font_size=screen.scaled_font_size(20),
        color=Colors.BLACK,
        align=TextAlign.LEFT,
    )
    
    while True:
        screen.fill()
        pg.mouse.set_visible(False)
        
        text_renderer.draw_text_block(
            exitScreenText,
            rel_x=0.05,
            rel_y=0.05,
            max_width=screen.abs_x(0.90),
            style=style,
            auto_fit=True,
            rel_max_y=0.95,
        )
        
        screen.update()
        
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    if logger:
                        logger.log_event("key_pressed", "escape")
                        logger.save()
                    pg.quit()
                    sys.exit()
                elif event.key == pg.K_f:
                    if logger:
                        logger.log_event("key_pressed", "f_continue")
                        logger.save()
                    return


def _get_additional_comments(win: pg.Surface, save_folder: str = "", subject_number: str = "") -> str:
    """Collect additional comments from participant."""
    screen = Screen(win)
    
    # Set up logging if save_folder provided
    logger = None
    if save_folder and subject_number:
        logger = ScreenEventLogger("additional_comments", save_folder, subject_number)
        logger.log_event("screen_presented", "additional_comments")
    
    text_input = TextInput(
        screen,
        mode=InputMode.FULL_ASCII,
        allow_spaces=True,
        allow_shift_symbols=True,
        placeholder="Enter comments or press Enter to skip..."
    )
    
    prompt = (
        "Please provide any additional comments you may have about the experiment below.\n"
        "If you have no additional comments, press Enter or Return to continue.\n\n"
        "**Additional Comments**"
    )
    
    
    result = text_input.run(prompt=prompt)
    
    if logger:
        logger.log_event("form_submitted", "comments_entered" if result else "skipped")
        logger.save()
    
    return result if result else ""


# =============================================================================
# MAIN FLOW
# =============================================================================

def run_end(
    win: pg.Surface,
    subject_number: str,
    block_names: list[str],
    save_folder: str,
    audio_engine=None,
) -> None:
    """
    Run the end-of-experiment flow: exit screen, summary data, cleanup.
    """
    # Log experiment end timestamp
    event_logger = get_global_logger()
    if event_logger:
        event_logger.log_experiment_end()
    
    # Show exit screen with logging
    _show_exit_screen(win, save_folder, subject_number)
    
    # Collect additional comments with logging
    comments = _get_additional_comments(win, save_folder, subject_number)
    
    # Save comments
    comments_path = os.path.join(save_folder, f'additional_comments_{subject_number}.txt')
    with open(comments_path, mode='w') as f:
        f.write(comments)
    
    # Write summary data with d-prime calculations
    _write_summary_data(subject_number, block_names, save_folder)
    
    # Cleanup audio if provided
    if audio_engine is not None:
        try:
            audio_engine.shutdown()
        except Exception:
            pass


def cleanup() -> None:
    """Clean up pygame resources."""
    pg.quit()
