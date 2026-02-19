"""
Auditory Superstitious Perception Experiment
=============================================
Main experiment orchestrator that coordinates all subtimelines.

Usage:
    python main_experimental_flow.py [--audio-device DEVICE_INDEX] [--dev-speakers]
"""

import os
import sys
import json

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'experiment_helpers'))

# Import subtimelines
from experiment_timeline.setup import run_setup, parse_args
from experiment_timeline.consent import collect_subject_info, create_save_folder, run_consent, show_non_consent
from experiment_timeline.intro import run_audio_level_test, preload_audio, run_intro
from experiment_timeline.blocks import run_blocks
from experiment_timeline.questionnaires_flow import run_questionnaires, save_sleepiness_data, stanford_sleepiness_scale
from experiment_timeline.end import run_end
from utils.eventLogger import init_global_logger


def _write_last_run_metadata(subject_number: str, save_folder: str) -> None:
    """Persist minimal run metadata for parent launcher process."""
    try:
        metadata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.last_experiment_run.json')
        payload = {
            "subject_number": subject_number,
            "save_folder": save_folder,
        }
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f)
    except Exception:
        pass


def main():
    """Main experiment flow."""
    
    # ==========================================================================
    # PHASE 1: SETUP
    # ==========================================================================
    
    # Parse command line args
    args = parse_args()

    # Starts pygame, initializes audio engine, and creates the experiment window
    win, audio_engine = run_setup(args)
    
    # ==========================================================================
    # PHASE 2: AUDIO PREPARATION & LEVEL TEST
    # ==========================================================================
    preload_audio(audio_engine)
    run_audio_level_test(win, audio_engine)
    
    # ==========================================================================
    # PHASE 3: COLLECT SUBJECT INFO
    # ==========================================================================
    subject_info = collect_subject_info(win)
    subject_number, save_folder = create_save_folder(subject_info['subject_number'])
    subject_info['subject_number'] = subject_number  # Update with final number
    _write_last_run_metadata(subject_number, save_folder)
    
    # Initialize event logger and log experiment start
    event_logger = init_global_logger(save_folder, subject_number)
    event_logger.log_experiment_start()
    
    # ==========================================================================
    # PHASE 4: CONSENT
    # ==========================================================================
    consented = run_consent(win, subject_info)
    if not consented:
        show_non_consent(win)
        return "Subject did not consent. No Save Folder Created."
    
    # ==========================================================================
    # PHASE 5: EXPERIMENT INTRODUCTION
    # ==========================================================================
    sleepiness_responses = []
    run_intro(win, save_folder=save_folder, subject_number=subject_number)
    
    # ==========================================================================
    # PHASE 6: EXPERIMENTAL BLOCKS
    # ==========================================================================
    block_names = run_blocks(
        win=win,
        subject_number=subject_number,
        save_folder=save_folder,
        audio_engine=audio_engine,
        sleepiness_responses=sleepiness_responses,
        stanford_sleepiness_scale_func=stanford_sleepiness_scale,
    )
    
    # ==========================================================================
    # PHASE 7: QUESTIONNAIRES
    # ==========================================================================
    # run_questionnaires(subject_number, win)
    save_sleepiness_data(subject_number, save_folder, sleepiness_responses)
    
    # ==========================================================================
    # PHASE 8: END & CLEANUP
    # ==========================================================================
    run_end(
        win=win,
        subject_number=subject_number,
        save_folder=save_folder,
        block_names=block_names,
        audio_engine=audio_engine,
    )

    return save_folder


if __name__ == '__main__':
    main()
