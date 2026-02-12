"""
Experiment Timeline Package
===========================
Contains subtimelines that orchestrate different phases of the experiment.

Subtimelines:
- setup: Initialize pygame, audio device, window
- consent: Consent flow screens
- intro: Experiment explanation/instructions
- blocks: Block-level flow (instructions, familiarization, trials)
- questionnaires_flow: Questionnaire administration
- end: Exit screen, save data, thank you

Usage:
    from experiment_timeline import (
        run_setup,
        run_consent,
        run_intro,
        run_blocks,
        run_questionnaires,
        run_end
    )
"""

from .setup import run_setup, pick_output_device, set_high_priority, parse_args
from .consent import run_consent, show_non_consent, collect_subject_info, create_save_folder
from .intro import run_intro, run_audio_level_test, preload_audio
from .blocks import run_blocks, prepare_blocks, run_trial_loop
from .questionnaires_flow import run_questionnaires, save_sleepiness_data, run_stanford_sleepiness
from .end import run_end, cleanup
