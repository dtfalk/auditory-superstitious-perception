# Superstitious Perception Experiment

## Updating the Code

In the VS Code terminal:
```
git pull origin master
```

## Experimenter Levers

All configurable settings are in `experiment_helpers/experimenterLevers.py`.

### Critical Settings for Running Subjects

## runExperiment.py
| Setting | Description |
|---------|-------------|
| `EXPERIMENTER_MODE` | **Must be `True` for live experiments.** Set in `runExperiment.py` (line 11). Disables Windows services that could interrupt the experiment. Will automatically disable itself if youa re not on Windows. |

## experiment_helpers\experimenterLevers.py
| Setting | Description |
|---------|-------------|
| `FORCE_WASAPI_OR_ASIO_EXCLUSIVE` | **Must be `True` for live experiments.** Ensures direct audio path for accurate playback. Will automatically disable itself if not on Windows.|
| `NUM_STIMULI_TO_SHOW` | **Must be `-1` for live experiments.** Shows all stimuli to the subject. You may set to a lower value if you are testing.|
| `MAX_PLAYS` | **Must be `1` for live experiments.** Forces subject to only listen to each stimulus once in the live trials.|
| `REMINDER_INTERVAL` | **Must be `15` for live experiments.** How often subject sees the reminder screen (e.g. every 15 trials). You may set to a lower value if you are testing.|
| `REMINDER_PLAYS` | **Must be `3` for live experiments.** Number of times subjects can listen to the audio during the reminder screens. You may set to a lower value if you are testing.|
| `FAMILIARIZATION_PLAYS` | **Must be `5` for live experiments.** How many familiarization listens the subject gets just before each block begins. You may set to a lower value if you are testing.|
| `PREFER_MOTU_ASIO` | **Must be `True` for live experiments.** Prefers MOTU devices on ASIO host API when available. |
| `SECTIONS_TO_SKIP` | **Must be `[]` for live experiments.** Empty list runs all sections. Options: `"audio_level_test"`, `"subject_info"`, `"consent"`, `"intro"`, `"blocks"`, `"questionnaires"` |
| `QUESTIONNAIRES_TO_SKIP` | **Must be `[]` for live experiments.** Empty list runs all questionnaires. Options: `"flow_state_scale"`, `"tellegen"`, `"vhq"`, `"launay_slade"`, `"dissociative_experiences"`, `"bais_v"`, `"bais_c"` |
| `SHORT_STIMULUS_FADEIN_ENABLED` | **Must be `True` for live experiments.** Enables DC click suppression fade-in for short stimuli. |
| `SHORT_STIMULUS_FADEIN_MS` | **Must be `50.0` for live experiments.** DC Fade-in duration in milliseconds. |
| `SHORT_STIMULUS_FADEIN_MAX_STIM_MS` | **Must be `5000` for live experiments.** Max stimulus length (ms) to apply DC fade-in. |
| `SHORT_STIMULUS_FADEOUT_ENABLED` | **Must be `True` for live experiments.** Enables DC click suppression fade-out for short stimuli. |
| `SHORT_STIMULUS_FADEOUT_MS` | **Must be `250.0` for live experiments.** DC Fade-out duration in milliseconds. |
| `SHORT_STIMULUS_FADEOUT_MAX_STIM_MS` | **Must be `5000` for live experiments.** Max stimulus length (ms) to apply DC fade-out. |

### Consent Form Variables

| Setting | Description |
|---------|-------------|
| `IRB_NUMBER` | Current IRB approval number |
| `STUDY_TITLE` | Study title shown in consent |
| `RESEARCHERS` | List of researcher names |
| `NUMBER_OF_CREDITS` | Compensation amount |
| `CREDIT_DENOMINATION` | Type of credits (e.g., "SONA credits") |

### Display & Trial Settings

| Setting | Description |
|---------|-------------|
| `WIN_WIDTH, WIN_HEIGHT` | Set by `prepareExperimentalScreen()`. Pass a number to select monitor by size rank. |
| `SENTENCE_TO_IMAGINE` | The target sentence participants listen for |
| `MIN_DB, MAX_DB` | Decibel range for audio leveling |

## Text Blocks That Need Editing

Located in `experiment_helpers/text_blocks/`:

### consentTextBlocks.py
Contains all consent form text. **Add your consent logic here** (study info, incentives, risks, confidentiality, contacts).

### experimentTextBlocks.py
Contains all experiment instruction text.

**Important:** Delete the line about the raffle in `explanationText_4` if not applicable:
```python
    - Please try your best. Better performance increases your chances of winning the raffle.\n\
```
## Experimenter Mode Note
Occasionally the script to exit experimenter mode hangs. Do not click the red x button. Just slick the terminal and press CTRL + C and it will proceed. 

## Setting up the experiment
1. Download this code (either as a zip or via git clone)
2. Create a Python virtual environment
```
python -m venv venv
```
3. Activate the virtual environment
```
./venv/scripts/activate
```
4. Download the required packages
```
./venv/scripts/pip.exe install -r requirements.txt
```

## Running the Experiment
1. Open a VS Code terminal (... -> Terminal -> New Terminal)
2. Run the following command in the terminal
```
./venv/scripts/activate
```
3. Run the following command in the terminal
```
python runExperiment.py
```
