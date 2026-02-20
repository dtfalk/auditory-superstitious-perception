import sys
import os
from utils.screenInfo import prepareExperimentalScreen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.screenInfo import prepareExperimentalScreen

# =================================================
# CONSENT FORM VARIABLES
# =================================================

# IRB number if you need to switch it
IRB_NUMBER = 'IRB24-1770'

# Change study title name
STUDY_TITLE = "Superstitious Perception"

# Researcher Names To include multiple names follow python list format
# (e.g. RESEARCHERS = ["John Doe", "Mary Sue", "Jane Doe"])
RESEARCHERS = ["Shannon Heald"]

# Number of experimental credits to give the subject
NUMBER_OF_CREDITS = '1.5'

# Name of the experimental credit currency
CREDIT_DENOMINATION = 'SONA credits' 

# =================================================
# DISPLAY AND LOGISTICAL VARIABLES
# =================================================

# Allows you to choose which monitor you want the experiment to display on
# Imagine you have 10 connected monitors and we order them by screen size from smallest to largest
# prepareExperimentalScreen(1)  ---> Experiment displays on the smallest monitor
# prepareExperimentalScreen(10) ---> Experiment displays on the largest monitor
# prepareExperimentalScreen(2)  ---> Experiment displays on the second smallest monitor
# prepareExperimentalScreen(8)  ---> Experiment displays on the third largest monitor
#
# Notes: 
#   1. If you don't input a number (i.e. "prepareExperimentalScreen()"), then it chooses the largest monitor
#   2. If you have only one screen then it will use that screen
WIN_WIDTH, WIN_HEIGHT = prepareExperimentalScreen()

# The sentence that the subject is listening for
# Change this if you ever make your own stimuli based on a different sentence
SENTENCE_TO_IMAGINE = "The Picture Hung on the Wall"

# Minimum and maximum decibles for audio leveling
MIN_DB = 68
MAX_DB = 70

# =============================================================================
# TRIAL CONFIGURATION
# =============================================================================

# Maximum number of times a participant can replay audio during a trial
MAX_PLAYS = 1

# How often to show periodic reminders (every N trials)
REMINDER_INTERVAL = 1

# Max plays allowed during periodic reminder screens
REMINDER_PLAYS = 1

# Max plays allowed during target familiarization screens
FAMILIARIZATION_PLAYS = 1

# Set to -1 to show all stimuli
# Otherwise will shown the specified number of stimuli per block
# (useful for testing/development)
NUM_STIMULI_TO_SHOW = 5

# Needs to be set for live experiments, but can be set to False for testing/development
# Ensures a direct path between headphones and the audio engine, which is necessary for accurate audio level testing and playback
FORCE_WASAPI_OR_ASIO_EXCLUSIVE = True

# If True, prefer MOTU devices on ASIO host API when available (easy to disable/remove later)
PREFER_MOTU_ASIO = True

# Optional click suppression for short one-shot stimuli using appended ramps.
# These ramps are appended before/after the clip without modifying the original samples.
SHORT_STIMULUS_FADEIN_ENABLED = True
SHORT_STIMULUS_FADEIN_MS = 10.0
SHORT_STIMULUS_FADEIN_MAX_STIM_MS = 5000

SHORT_STIMULUS_FADEOUT_ENABLED = True
SHORT_STIMULUS_FADEOUT_MS = 10.0
SHORT_STIMULUS_FADEOUT_MAX_STIM_MS = 5000