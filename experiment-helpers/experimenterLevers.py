
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.screenInfo import prepareExperimentalScreen

# Number of experimental credits to give the subject
number_of_credits = '1.5'

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
SENTENCE_TO_IMAGINE = "The picture hung on the wall."

# =============================================================================
# TRIAL CONFIGURATION
# =============================================================================

# Maximum number of times a participant can replay audio during a trial
MAX_PLAYS = 1

# How often to show periodic reminders (every N trials)
REMINDER_INTERVAL = 25

# Max plays allowed during target familiarization screens
FAMILIARIZATION_MAX_PLAYS = 5

# Max plays allowed during periodic reminder screens
REMINDER_MAX_PLAYS = 3