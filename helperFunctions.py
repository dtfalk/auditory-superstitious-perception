import os
import sys
import io
import csv
from random import choice
from scipy.stats import norm
from scipy.signal import resample_poly
import pygame as pg
import pytz
from datetime import datetime
import wave
import numpy as np
from constants import *


imageWidth, imageHeight = 50, 50
imageSize = imageWidth * imageHeight

# class for the buttons the user will see
class Button:

    # initializes an instance of a button
    def __init__(self, buttonType, questionnaireName, text, i, yPosQuestion):

        surface = pg.display.get_surface()
        if surface:
            current_w, current_h = surface.get_size()
        else:
            current_w, current_h = winWidth, winHeight

        base_medium_font = max(14, current_h // 20)

         # creates a box to click and text for questionnaire options
        if buttonType == 'option':
            self.fontSize = base_medium_font
            if questionnaireName == 'binary':
                scalar = 1.4
            elif questionnaireName == 'tellegen':
                scalar = 1.75
            elif questionnaireName == 'launay':
                scalar = 1.4
            elif questionnaireName == 'dissociative':
                scalar = 1.5

            buffer = current_h // 20

            # Make option button size proportional to screen
            button_size = int(0.015 * min(current_w, current_h))
            button_size = max(button_size, self.fontSize)

            # Binary options (e.g., Yes/No) should always be a single vertical column
            if questionnaireName == 'binary':
                option_index = max(0, i - 1)
                start_y = int(min(yPosQuestion + buffer, 0.60 * current_h))
                x = int(0.08 * current_w)
                y = start_y + int(option_index * scalar * self.fontSize)
                self.coords = (x, y, button_size, button_size)
                self.text_x = self.coords[0] + 1.5 * button_size
                self.text_y = self.coords[1] - 0.1 * button_size
            else:
                spacing = scalar * i * self.fontSize
                maxY = (0.85 * current_h) - self.fontSize

                self.coords = ((0.05 * current_w) + (0.45 * current_w) * ((yPosQuestion + spacing + buffer) // maxY),
                               yPosQuestion + buffer + (spacing % (maxY - (yPosQuestion + buffer))),
                               button_size,
                               button_size)
                self.text_x = self.coords[0] + 1.5 * button_size
                self.text_y = self.coords[1] - 0.1 * button_size
            
        else: # creates the submit button so the user may submit their response
            self.fontSize = int(0.85 * base_medium_font)
            
            # Calculate text dimensions for responsive sizing
            font = pg.font.SysFont("times new roman", self.fontSize)
            text_surface = font.render(text, True, BLACK)
            text_width, text_height = text_surface.get_size()
            
            # Make button size proportional to screen and text
            padding_x = int(0.02 * current_w)  # 2% of screen width padding
            padding_y = int(0.01 * current_h)  # 1% of screen height padding
            button_width = text_width + (2 * padding_x)
            button_height = text_height + (2 * padding_y)
            
            # Ensure minimum size (proportional to screen)
            min_width = int(0.08 * current_w)
            min_height = int(0.04 * current_h)
            button_width = max(button_width, min_width)
            button_height = max(button_height, min_height)
            
            # Center the button horizontally, position vertically at 85% of screen height
            button_x = (current_w - button_width) // 2
            button_y = int(0.85 * current_h)
            
            self.coords = (button_x, button_y, button_width, button_height)
            # Text positioning will be handled by centering in draw method
            self.text_x = 0.46 * current_w  # Keep for compatibility, but draw() will center
            self.text_y = self.coords[1]
        
        self.color = WHITE
        self.text = text
        self.checkbox = pg.Rect(self.coords)
        self.checked = False # is the checkbox checked or not
        self.buttonType = buttonType # question option vs submit button
    
    # draw function for each button
    def draw(self, win):
        if self.buttonType == 'submit':
            # Enhanced styling for submit buttons
            # Use white background with black text
            button_color = WHITE  # White background
            text_color = BLACK    # Black text
            
            # Draw filled rectangle with border
            pg.draw.rect(win, button_color, self.checkbox)
            pg.draw.rect(win, BLACK, self.checkbox, 3)  # Black border
            
            # Center the text properly
            text_surface = pg.font.SysFont("times new roman", self.fontSize).render(self.text, True, text_color)
            text_rect = text_surface.get_rect(center=self.checkbox.center)
            win.blit(text_surface, text_rect)
        else:
            # Enhanced styling for option buttons - add black border
            pg.draw.rect(win, self.color, self.checkbox)
            pg.draw.rect(win, BLACK, self.checkbox, 2)  # Black border for option buttons
            text_surface = pg.font.SysFont("times new roman", self.fontSize).render(self.text, True, BLACK)     
            win.blit(text_surface, (self.text_x, self.text_y))

    # handles button clicks
    def handleClick(self, buttons):
        if self.buttonType == 'option':
            self.checked = not self.checked # switch button state
            if self.checked: # if selected, change color to red
                self.color = RED
            else: # if unselected, change color to white
                self.color = WHITE 
            self.unselectOthers(buttons)
            return None
        else:
            for button in buttons:
                if button.checked and button != self:
                    self.checked = True
                    return button.text
            
    # unselects all other questions
    def unselectOthers(self, buttons):
        for button in buttons:

            # don't unclick button just clicked or "unclick" the submit button
            if button == self or button.buttonType != 'option':
                continue

            # if something is already checked, then uncheck it
            if button.checked:
                button.checked = False
                button.color = WHITE

# Audio resampling helpers
def load_wav_mono_int16(path: str):
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

def resample_int16(x16: np.ndarray, fs_in: int, fs_out: int) -> np.ndarray:
    if fs_in == fs_out:
        return x16

    x = x16.astype(np.float32) / 32768.0
    g = np.gcd(fs_in, fs_out)
    y = resample_poly(x, fs_out // g, fs_in // g)
    y = np.clip(y, -1.0, 1.0)
    return (y * 32767.0).astype(np.int16)


# Cached WAV loading (prevents disk I/O during trials)
_PCM_CACHE: dict[tuple[str, int], np.ndarray] = {}
_CONCAT_CACHE: dict[tuple[str, str, bool, int, int], np.ndarray] = {}


def get_pcm16_mono(path: str, fs_out: int) -> np.ndarray:
    """Load a WAV once, convert to mono int16, resample to fs_out, and cache."""
    key = (os.path.abspath(path), int(fs_out))
    pcm = _PCM_CACHE.get(key)
    if pcm is not None:
        return pcm

    x16, fs_in = load_wav_mono_int16(path)
    y16 = resample_int16(x16, fs_in, fs_out)
    _PCM_CACHE[key] = y16
    return y16


def preload_pcm16_mono(paths: list[str], fs_out: int):
    """Best-effort preload of multiple WAV paths into the cache."""
    for p in paths:
        if not p:
            continue
        if os.path.exists(p):
            get_pcm16_mono(p, fs_out)

# This block of code handles lab streaming layer functionality
# =======================================================================
# =======================================================================

# # Initializes lab streaming layer outlet
# def initializeOutlet():
#     infoEvents = StreamInfo('eventStream', 'events', 1, 0, 'string')
#     outlet = StreamOutlet(infoEvents)
#     return outlet

# # pushes a sample to the outlet
# def pushSample(outlet, tag):
#     outlet.push_sample([tag])

# =======================================================================
# =======================================================================



# These functions are for collecting/saving user/experiment data
# =======================================================================
# =======================================================================

# stops game execution until a particular key is pressed
def waitKey(key):

    # just keep waiting until the relevant key is pressed
    while True:
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == key:
                    return
                elif event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()


def _current_window_size(win):
    """Best-effort current window size (works even if constants winWidth/winHeight are wrong)."""
    try:
        w, h = win.get_size()
        if w and h:
            return w, h
    except Exception:
        pass
    surface = pg.display.get_surface()
    if surface:
        return surface.get_width(), surface.get_height()
    return winWidth, winHeight


def _wrap_text_to_width(font: pg.font.Font, text: str, max_width: int):
    """Word-wrap `text` so each rendered line is <= max_width."""
    if not text:
        return [""]
    if max_width <= 0:
        return [text]

    words = text.split()
    if not words:
        return [""]

    lines = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if font.size(trial)[0] <= max_width:
            current = trial
            continue

        # If the current line is already too wide (single very long word), split it.
        if font.size(current)[0] > max_width:
            chunk = ""
            for ch in current:
                trial_chunk = chunk + ch
                if font.size(trial_chunk)[0] <= max_width or not chunk:
                    chunk = trial_chunk
                else:
                    lines.append(chunk)
                    chunk = ch
            if chunk:
                lines.append(chunk)
            current = word
        else:
            lines.append(current)
            current = word

    if font.size(current)[0] > max_width:
        chunk = ""
        for ch in current:
            trial_chunk = chunk + ch
            if font.size(trial_chunk)[0] <= max_width or not chunk:
                chunk = trial_chunk
            else:
                lines.append(chunk)
                chunk = ch
        if chunk:
            lines.append(chunk)
    else:
        lines.append(current)

    return lines


def _blit_wrapped_centered(
    win,
    font: pg.font.Font,
    text: str,
    center_x: int,
    y_pos: int,
    max_width: int,
    color,
    line_step: int | None = None,
):
    """Draw centered wrapped text, returning the next y position."""
    if line_step is None:
        line_step = font.get_linesize()

    for line in _wrap_text_to_width(font, text, max_width):
        if line:
            surf = font.render(line, True, color)
            rect = surf.get_rect(center=(center_x, y_pos))
            win.blit(surf, rect)
        y_pos += line_step
    return y_pos


# function to draw/fit a multiline message to the screen
def multiLineMessage(text, textsize, win, xPos_start=None, yPos_start=None, xMax=None, yMax=None):

    current_w, current_h = _current_window_size(win)
    if xPos_start is None:
        xPos_start = 0.05 * current_w
    if yPos_start is None:
        yPos_start = 0.05 * current_h
    if xMax is None:
        xMax = 0.95 * current_w
    if yMax is None:
        yMax = 0.95 * current_h

    # set font and text color
    font = pg.font.SysFont("times new roman", textsize)
    color = BLACK

    # Function to calculate if the text fits within the designated area
    def fitsWithinArea(text, font):

        # starting x and y coordinate for the text
        xPos = xPos_start
        yPos = yPos_start

        # Get line height based on font size
        lineHeight = font.get_linesize() 
        lines = text.split('\n')
        for line in lines:

            # Handle empty lines for consecutive newlines
            if line == '':
                yPos += lineHeight
            
            # Handle non-empty lines
            else:
                words = line.split()
                for word in words:
                    word_surface = font.render(word, True, color)
                    wordWidth, _ = word_surface.get_size()

                    # Check if new word exceeds the line width
                    if xPos + wordWidth > xMax: 

                        # Reset to start of the line
                        xPos = xPos_start

                        # Move down by the height of the previous line
                        yPos += lineHeight

                    # Check if adding another line exceeds the page height
                    if yPos + lineHeight > yMax:
                        return False
                    
                    # Blit here for size calculation
                    win.blit(word_surface, (xPos, yPos))

                    # Move xPos for the next word, add space
                    xPos += wordWidth + font.size(" ")[0] 
                
                # reset x position and increment y position by height of text
                xPos = xPos_start
                yPos += lineHeight
        return True

    # Adjust font size until the text fits within the area
    while not fitsWithinArea(text, font) and textsize > 1:
        textsize -= 1
        font = pg.font.SysFont("times new roman", textsize)

    # Draw the background and boundaries only once
    win.fill(backgroundColor)

    # Now draw the text with the properly adjusted font size
    xPos = xPos_start
    yPos = yPos_start
    lineHeight = font.get_linesize()
    lines = text.split('\n')

    # iterate over each line
    for line in lines:

        # Handle empty lines for consecutive newlines
        if line == '':
            yPos += lineHeight

        # Handle non-empty lines
        else:

            # split the line into its constituent words
            words = line.split()

            # iterate over each words
            for word in words:

                # render the word and get the size of the word
                word_surface = font.render(word, True, color)
                wordWidth, _ = word_surface.get_size()

                # Check if word exceeds line width
                if xPos + wordWidth > xMax:

                    # reset x position and increment y position
                    xPos = xPos_start
                    yPos += lineHeight
                
                # draw word
                win.blit(word_surface, (xPos, yPos))

                # increment x position by word width
                xPos += wordWidth + font.size(" ")[0]
            
            # reset x position and increment y position
            xPos = xPos_start
            yPos += lineHeight

    return yPos

# returns true if user enters a valid key (a-z or 0-9 or spacebar)
def isValid(key, requestType):

    # response only allows a-z and spaces
    if 'name' in requestType or requestType == 'Signature':
        if 97 <= key <= 122 or key == 32:
            return True
    
    elif requestType == 'Additional Comments' or requestType == 'selfReflect_explanation'or requestType == 'selfReflect_changes':
        if 32 <= key <= 126:
            return True
        
    # subject number and level selection only allow digits
    elif requestType == 'subject number':
        if 48 <= key <= 57:
            return True
    
    # subejct email
    else:
        if (97 <= key <= 122) or (48 <= key <= 57) or key == 64 or key == 46 or key == 45:
            return True
        
    return False
    
# gets user's response and subject ID
def getSubjectInfo(requestType, win):

    response = "" 
    prompter = requestType
    if requestType in ['selfReflect_changes', 'selfReflect_explanation', 'imagination_rule_following']:
        prompter = 'Response'
    exit = False

    # event loop
    while True:
        for event in pg.event.get():

            # if user presses a key, then...
            if event.type == pg.KEYDOWN:

                # lets the user quit
                if event.key == pg.K_ESCAPE:
                    exit_key = pg.K_ESCAPE
                    exit = True
                    
                # if they press enter or return, then...
                if event.key == pg.K_KP_ENTER or event.key == pg.K_RETURN:
                    
                    if len(response) > 0:
                        
                        # set the exit key to the key they pressed and set the exit boolean to true
                        exit_key = event.key
                        exit = True
                
                # delete last character if they press backspace or delete
                elif event.key == pg.K_BACKSPACE or event.key == pg.K_DELETE:
                    response = response[:-1] 
                
                # if they enter a valid key (a-z, 0-9, or spacebar)
                elif isValid(event.key, requestType):
                    if (pg.key.get_mods() & pg.KMOD_CAPS) or (pg.key.get_mods() & pg.KMOD_SHIFT):
                        if event.key == 50:
                            response += '@'
                        else:
                            response = response + chr(event.key).upper()
                    else:
                        response = response + chr(event.key).lower()
        if exit == True:
            break
        win.fill(backgroundColor) 
        if requestType == 'Signature':
            text = "Please type your name to confirm that you consent to participate in this study. Press Enter or Return to submit.\n\n"
        elif requestType == 'selfReflect_explanation':
            text = 'During the previous block, how did you decide whether or not the word "Wall" was in each of the stimuli? What were you thinking about or considering as you made that decision?\n'
        elif requestType == 'selfReflect_changes':
            text = 'Did your methodology change or evolve over the course of the previous block?\n'
        elif requestType == 'imagination_rule_following':
            text = 'During this block did you imagine the sentence before playing the simuli and then click "Play Audio" at the moment you would have imagined the word "Wall"? Please begin your response with either "Yes." or "No." You may include additional information after typing "Yes." or "No."\n'
        elif requestType == 'Additional Comments':
            text = 'Please provide any additional comments you may have about the experiment below. If you have no additional comments, press Enter or Return to continue.\n'
        else:
            text = "Please enter the requested information. Then press Enter or Return to continue. Press ESC to exit or inform the observer of your decision. \n\n"
        pg.mouse.set_visible(False)
        multiLineMessage(text + f'\n{prompter}: ' + response, mediumFont, win)
        pg.display.flip()

    # if the user pressed either return or enter, then we continue
    if exit_key == pg.K_RETURN or exit_key == pg.K_KP_ENTER:
        return response 
    
    # otherwise, they pressed the exit key and we exit the game
    else:
        pg.quit()
        sys.exit()
        

# records a user's response to a given trial
def recordResponse(subjectNumber, block, stimulusNumber, stimulusType, response, responseTime, saveFolder, play_count=1):
    
    # path to the save file
    filePath = os.path.join(saveFolder, f'{block}_{subjectNumber}.csv')

    # prepare the header and the data
    header = ['Subject Number', 'Block Scheme', 'Stimulus Number', 'Stimulus Type', 'Subject Response', 'Response Time', 'Play Count']
    data = [subjectNumber, block, stimulusNumber, stimulusType, response, '%.5f'%(responseTime / 1000), play_count]

    # if csv file does not exist, then write the header and the data
    if not os.path.exists(filePath):
        with open(filePath, mode = 'w', newline = '') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerow(data)

    # otherwise just write the data
    else:
        with open(filePath, mode = 'a', newline = '') as file:
            writer = csv.writer(file)
            writer.writerow(data)
    return

# calculates a dprime score
def calculateDprime(hits, misses, correctRejections, falseAlarms):
    
    try: 
        hitRate = hits / (hits + misses)
        falseAlarmRate = falseAlarms / (falseAlarms + correctRejections)
    except:
        return 'NaN'

    # values for fixing extreme d primes
    halfHit = 0.5 / (hits + misses)
    halfFalseAlarm = 0.5 / (falseAlarms + correctRejections)

    if hitRate == 1:
        hitRate = 1 - halfHit
    if hitRate == 0:
        hitRate = halfHit
    if falseAlarmRate == 1:
        falseAlarmRate = 1 - halfFalseAlarm
    if falseAlarmRate == 0:
        falseAlarmRate = halfFalseAlarm

    # calculate z values
    hitRateZScore = norm.ppf(hitRate)
    falseAlarmRateZScore = norm.ppf(falseAlarmRate)

    # calculate d prime
    dprime = hitRateZScore - falseAlarmRateZScore

    return dprime

# writes summary data about user's performance
def writeSummaryData(subjectNumber, block_names, saveFolder):

    # Path to where we save the data
    filePath = os.path.join(saveFolder, f'summaryData_{subjectNumber}.csv')

    # add files in correct order so we load and calculate data in correct order
    dataFiles = []
    for block in block_names:
        dataFiles.append(os.path.join(saveFolder, f'{block}_{subjectNumber}.csv'))
    

    # caclulate dprimes for uncorrelated distractors
    dprimes = []
    for dataFile in dataFiles:
        with open(dataFile, mode = 'r', newline = '') as f:
            reader = csv.reader(f)
            lines = list(reader)
            header = lines[0]
            data = lines[1:]

            # create a dictionary to easily access data entries
            indices = {}
            for i, entry in enumerate(header):
                indices[entry] = i

            # collecting relevant data for calculating dprime
            hits = 0
            misses = 0
            falseAlarms = 0
            correctRejections = 0

            for entry in data:
                if entry[indices['Stimulus Type']] == 'target' and entry[indices['Subject Response']] == 'target':
                    hits += 1
                elif entry[indices['Stimulus Type']] == 'target' and entry[indices['Subject Response']] == 'distractor':
                    misses += 1
                elif entry[indices['Stimulus Type']] == 'distractor' and entry[indices['Subject Response']] == 'target':
                    falseAlarms += 1
                else:
                    correctRejections += 1
            dprime = calculateDprime(hits, misses, correctRejections, falseAlarms)
            dprimes.append(dprime)

    # prepare header and data for writing
    summaryDataHeader = ['Subject Number',  'Block 1', 'Block 1 D-Prime', 'Block 2', 'Block 2 D-Prime']
    summaryData = [subjectNumber]
    for i, block in enumerate(block_names):
        summaryData.append(f'{block}')
        summaryData.append(dprimes[i])


    # write results to summary data file
    with open(filePath, mode = 'w', newline = '') as f:
        writer = csv.writer(f)
        writer.writerow(summaryDataHeader)
        writer.writerow(summaryData)
        

# =======================================================================
# =======================================================================
        
# a lists of the stimuli
def getStimuli():
    
    # get the current file's path
    stimuliDir = os.path.join(os.path.dirname(__file__), 'audio_stimuli')

    # list of file names as paths for full sentence audio
    full_sentence_targets = [os.path.join(stimuliDir, 'full_sentence', 'targets', fileName) 
                             for fileName in os.listdir(os.path.join(stimuliDir, 'full_sentence', 'targets'))]
    full_sentence_distractors = [os.path.join(stimuliDir, 'full_sentence', 'distractors', fileName) 
                                 for fileName in os.listdir(os.path.join(stimuliDir, 'full_sentence', 'distractors'))]

    # list of file names as paths for iamgine sentence audio
    imagined_sentence_targets = [os.path.join(stimuliDir, 'imagined_sentence', 'targets', fileName) 
                            for fileName in os.listdir(os.path.join(stimuliDir, 'imagined_sentence', 'targets'))]
    imagined_sentence_distractors = [os.path.join(stimuliDir, 'imagined_sentence', 'distractors', fileName) 
                                for fileName in os.listdir(os.path.join(stimuliDir, 'imagined_sentence', 'distractors'))]

    return full_sentence_targets, full_sentence_distractors, imagined_sentence_targets, imagined_sentence_distractors 


def preload_experiment_audio(fs_out: int = 44100):
    """Preload all known experiment audio into the PCM cache (no disk I/O during trials)."""
    audio_stimuli_dir = os.path.join(os.path.dirname(__file__), 'audio_stimuli')

    full_sentence_targets, full_sentence_distractors, imagined_sentence_targets, imagined_sentence_distractors = getStimuli()

    extras = [
        os.path.join(audio_stimuli_dir, 'fullsentenceminuswall.wav'),
        os.path.join(audio_stimuli_dir, 'fullsentence.wav'),
        os.path.join(audio_stimuli_dir, 'targetwall.wav'),
        os.path.join(audio_stimuli_dir, 'target_example.wav'),
        os.path.join(audio_stimuli_dir, 'distractor_example.wav'),
        os.path.join(audio_stimuli_dir, '60s_background_noise.wav'),
    ]

    preload_pcm16_mono(
        full_sentence_targets
        + full_sentence_distractors
        + imagined_sentence_targets
        + imagined_sentence_distractors
        + extras,
        fs_out,
    )

    # Precompute prefix+stimulus concatenations for the full-sentence block.
    prefix = os.path.join(audio_stimuli_dir, 'fullsentenceminuswall.wav')
    if os.path.exists(prefix):
        for stim in full_sentence_targets + full_sentence_distractors:
            if os.path.exists(stim):
                concatenate_wavs(prefix, stim, add_gap=False, fs_out=fs_out)



# This code is for showing various message screens (e.g. experiment explanation)
# and functions that display images
# =======================================================================
# =======================================================================

def showBlockExamples(win, audio_engine, block_name: str | None = None):
    """Show targets + actual target audio + distractors on a single screen.

    Layout:
    - Top row: 5 target example buttons
    - Middle: one "Actual Audio" button
    - Bottom row: 5 distractor example buttons

    The subject is forced (via the existing highlight/grey-out logic) to play in this order:
    Actual -> Target 1 -> Actual -> Distractor 1 -> Actual -> Target 2 -> ... -> Distractor 5
    """
    pg.mouse.set_visible(True)

    audio_stimuli_dir = os.path.join(os.path.dirname(__file__), 'audio_stimuli')
    examples_targets_dir = os.path.join(audio_stimuli_dir, 'examples', 'targets')
    examples_distractors_dir = os.path.join(audio_stimuli_dir, 'examples', 'distractors')

    if not os.path.isdir(examples_targets_dir):
        raise FileNotFoundError(f"Examples folder not found: {examples_targets_dir}")
    if not os.path.isdir(examples_distractors_dir):
        raise FileNotFoundError(f"Examples folder not found: {examples_distractors_dir}")

    target_files = sorted([p for p in os.listdir(examples_targets_dir) if p.lower().endswith('.wav')])
    distractor_files = sorted([p for p in os.listdir(examples_distractors_dir) if p.lower().endswith('.wav')])

    # The UI requires 5 items in each row.
    if len(target_files) < 5:
        raise FileNotFoundError(f"Need 5 target example wavs in {examples_targets_dir}, found {len(target_files)}")
    if len(distractor_files) < 5:
        raise FileNotFoundError(f"Need 5 distractor example wavs in {examples_distractors_dir}, found {len(distractor_files)}")

    target_files = target_files[:5]
    distractor_files = distractor_files[:5]

    # Actual target audio
    if block_name == 'imagined_sentence':
        actual_target_path = os.path.join(audio_stimuli_dir, 'targetwall.wav')
        actual_button_label = 'Actual Audio'
    else:
        actual_target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
        actual_button_label = 'Actual Audio'

    fs_out = int(audio_engine.fs)
    actual_pcm = get_pcm16_mono(actual_target_path, fs_out)

    if block_name == 'full_sentence':
        prefix_path = os.path.join(audio_stimuli_dir, 'fullsentenceminuswall.wav')
        targets_pcm = [concatenate_wavs(prefix_path, os.path.join(examples_targets_dir, f), add_gap=False, fs_out=fs_out) for f in target_files]
        distractors_pcm = [concatenate_wavs(prefix_path, os.path.join(examples_distractors_dir, f), add_gap=False, fs_out=fs_out) for f in distractor_files]
    else:
        targets_pcm = [get_pcm16_mono(os.path.join(examples_targets_dir, f), fs_out) for f in target_files]
        distractors_pcm = [get_pcm16_mono(os.path.join(examples_distractors_dir, f), fs_out) for f in distractor_files]

    # Build forced sequence: A, T1, A, D1, A, T2, ... , A, D5 (no trailing A)
    sequence: list[tuple[str, int | None]] = [('actual', None)]
    for i in range(5):
        sequence.extend([('target', i), ('actual', None), ('distractor', i), ('actual', None)])
    sequence.pop()  # remove last trailing actual

    seq_index = 0
    last_audio_start = 0
    audio_duration = 0

    while True:
        current_w, current_h = _current_window_size(win)
        win.fill(backgroundColor)

        # Header/instructions
        header_font = pg.font.SysFont('times new roman', max(22, current_h // 28))
        body_font = pg.font.SysFont('times new roman', max(18, current_h // 36))
        y_pos = int(0.07 * current_h)

        header = 'Examples'
        if block_name == 'imagined_sentence':
            header = 'Examples (Imagined Sentence)'
        elif block_name == 'full_sentence':
            header = 'Examples (Full Sentence)'

        y_pos = _blit_wrapped_centered(
            font=header_font,
            win=win,
            text=header,
            center_x=current_w // 2,
            y_pos=y_pos,
            max_width=int(0.92 * current_w),
            color=BLACK,
        )
        y_pos += 8

        instruction_lines = [
            'You must listen to all of the example audio samples before you continue.',
            'Please listen to each audio sample carefully.',
            'The blue, highlighted button indicates which audio sample you must play next.',
            'When the "Continue" button turns green, you may click it to proceed.'
        ]
        for line in instruction_lines:
            y_pos = _blit_wrapped_centered(
                font=body_font,
                win=win,
                text=line,
                center_x=current_w // 2,
                y_pos=y_pos,
                max_width=int(0.92 * current_w),
                color=BLACK,
            )
            y_pos += 4

        # Timing gate
        current_time = pg.time.get_ticks()
        time_since_last = current_time - last_audio_start
        audio_still_playing = (last_audio_start != 0) and (time_since_last < audio_duration)

        active_kind, active_idx = sequence[seq_index] if seq_index < len(sequence) else (None, None)

        # Layout: three rows of buttons
        row_button_w = int(0.14 * current_w)
        row_button_h = int(0.08 * current_h)
        row_gap = int(0.03 * current_h)
        col_count = 5
        spacing = int((current_w - (row_button_w * col_count)) / (col_count + 1))

        top_y = int(y_pos + 0.05 * current_h)
        mid_y = top_y + row_button_h + row_gap
        bot_y = mid_y + row_button_h + row_gap

        target_rects: list[pg.Rect] = []
        distractor_rects: list[pg.Rect] = []
        for i in range(col_count):
            x = spacing + i * (row_button_w + spacing)
            target_rects.append(pg.Rect(x, top_y, row_button_w, row_button_h))
            distractor_rects.append(pg.Rect(x, bot_y, row_button_w, row_button_h))

        actual_w = int(0.28 * current_w)
        actual_h = row_button_h
        actual_rect = pg.Rect((current_w - actual_w) // 2, mid_y, actual_w, actual_h)

        # Continue button
        continue_w = int(0.18 * current_w)
        continue_h = int(0.06 * current_h)
        continue_rect = pg.Rect((current_w - continue_w) // 2, bot_y + row_button_h + int(0.06 * current_h), continue_w, continue_h)
        all_done = (seq_index >= len(sequence))
        continue_enabled = all_done and (not audio_still_playing)

        disabled_color = [180, 180, 180]  # distinct from backgroundColor (currently GREY)

        def _draw_button(rect: pg.Rect, label: str, is_active: bool):
            if is_active and not audio_still_playing:
                color = BLUE
                text_color = WHITE
            else:
                color = disabled_color
                text_color = BLACK
            pg.draw.rect(win, color, rect)
            pg.draw.rect(win, BLACK, rect, 2)
            lab = pg.font.SysFont('times new roman', max(14, current_h // 44)).render(label, True, text_color)
            win.blit(lab, lab.get_rect(center=rect.center))

        # Labels above rows
        label_font = pg.font.SysFont('times new roman', max(18, current_h // 40))
        t_lab = label_font.render('Targets', True, BLACK)
        d_lab = label_font.render('Distractors', True, BLACK)
        win.blit(t_lab, (spacing, max(0, top_y - t_lab.get_height() - 6)))
        win.blit(d_lab, (spacing, max(0, bot_y - d_lab.get_height() - 6)))

        # Draw target buttons
        for i, rect in enumerate(target_rects):
            _draw_button(rect, f'Target {i+1}', (active_kind == 'target' and active_idx == i))

        # Draw actual button
        _draw_button(actual_rect, actual_button_label, (active_kind == 'actual'))

        # Draw distractor buttons
        for i, rect in enumerate(distractor_rects):
            _draw_button(rect, f'Distractor {i+1}', (active_kind == 'distractor' and active_idx == i))

        # Draw continue
        cont_color = GREEN if continue_enabled else disabled_color
        cont_text_color = BLACK if continue_enabled else WHITE
        pg.draw.rect(win, cont_color, continue_rect)
        pg.draw.rect(win, BLACK, continue_rect, 2)
        cont_label = pg.font.SysFont('times new roman', max(16, current_h // 38)).render('Continue', True, cont_text_color)
        win.blit(cont_label, cont_label.get_rect(center=continue_rect.center))

        # Progress indicator
        # prog_font = pg.font.SysFont('times new roman', max(14, current_h // 50))
        # prog_surf = prog_font.render(f"Step: {min(seq_index, len(sequence))}/{len(sequence)}", True, BLACK)
        # win.blit(prog_surf, (10, 10))

        pg.display.flip()

        for event in pg.event.get():
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                pg.quit(); sys.exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                mouse = pg.mouse.get_pos()
                current_time = pg.time.get_ticks()
                time_since_last = current_time - last_audio_start
                audio_still_playing = (last_audio_start != 0) and (time_since_last < audio_duration)

                if continue_rect.collidepoint(mouse) and continue_enabled:
                    return

                if audio_still_playing or seq_index >= len(sequence):
                    continue

                kind, idx = sequence[seq_index]
                clicked_correct = False
                if kind == 'actual' and actual_rect.collidepoint(mouse):
                    audio_duration = playAudioStimulus(audio_engine, actual_pcm)
                    clicked_correct = True
                elif kind == 'target' and idx is not None and target_rects[idx].collidepoint(mouse):
                    audio_duration = playAudioStimulus(audio_engine, targets_pcm[idx])
                    clicked_correct = True
                elif kind == 'distractor' and idx is not None and distractor_rects[idx].collidepoint(mouse):
                    audio_duration = playAudioStimulus(audio_engine, distractors_pcm[idx])
                    clicked_correct = True

                if clicked_correct:
                    last_audio_start = current_time
                    seq_index += 1


# shows the example audio stimuli (kept for backward-compatibility with the original intro)
def showExamples(win, text = '', audio_engine=None):
    # Backward-compatible wrapper (defaults to full-sentence examples)
    if audio_engine is None:
        raise RuntimeError("showExamples() now requires audio_engine")
    showBlockExamples(win, audio_engine=audio_engine)


def showBlockInstructions(win, block_name: str, audio_engine):
    """One block-specific instruction screen + the example-audio screen."""
    if block_name == 'imagined_sentence':
        text = imaginedSentenceBlockInstructionsText
    else:
        text = fullSentenceBlockInstructionsText

    win.fill(backgroundColor)
    multiLineMessage(text, mediumFont, win)
    pg.display.flip()
    waitKey(pg.K_SPACE)

    showBlockExamples(win, audio_engine, block_name=block_name)
    pg.mouse.set_visible(False)


def showPreTrialQuickResponseScreen(win, block_name):
    """Instruction screen shown immediately before the first trial of each block."""
    pg.mouse.set_visible(False)
    win.fill(backgroundColor)
    if block_name == "full_sentence":
        multiLineMessage(preTrialQuickResponseTextFullSentence, mediumFont, win)
    else:
        multiLineMessage(preTrialQuickResponseTextImaginedSentence, mediumFont, win)
    pg.display.flip()
    waitKey(pg.K_SPACE)


# explains the experiment to the subject
def experimentExplanation(win):
    win.fill(backgroundColor)
    multiLineMessage(explanationText_1, mediumFont, win)
    pg.display.flip()
    waitKey(pg.K_SPACE)

    win.fill(backgroundColor)
    multiLineMessage(explanationText_2, mediumFont, win)
    pg.display.flip()
    waitKey(pg.K_SPACE)

    win.fill(backgroundColor)
    multiLineMessage(explanationText_3, mediumFont, win)
    pg.display.flip()
    waitKey(pg.K_SPACE)

    win.fill(backgroundColor)
    multiLineMessage(explanationText_4, mediumFont, win)
    pg.display.flip()
    waitKey(pg.K_SPACE)

    # win.fill(backgroundColor)
    # multiLineMessage(explanationText_5, mediumFont, win)
    # pg.display.flip()
    # waitKey(pg.K_SPACE)

# instructions for the real trials
def finalInstructions(win):
    win.fill(backgroundColor)
    multiLineMessage(realText, mediumFont, win)
    pg.display.flip()
    waitKey(pg.K_SPACE)

# instructions for the real trials
def realInstructionsAlt(win):
    win.fill(backgroundColor)
    multiLineMessage(realTextAlt, mediumFont, win)
    pg.display.flip()
    waitKey(pg.K_SPACE)

# break screen thanking the participant
def breakScreen(i, win):
    win.fill(backgroundColor)
    multiLineMessage(breakScreenText(i), mediumFont, win)
    pg.display.flip()
    waitKey(pg.K_f)

# exit screen thanking the participant
def exitScreen(subjectNumber, win):
    pg.mouse.set_visible(False)
    win.fill(backgroundColor)
    multiLineMessage(exitScreenText, mediumFont, win)
    pg.display.flip()
    waitKey(pg.K_f)
    additionalComments = getSubjectInfo('Additional Comments', win)
    with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'additional_comments.txt_{subjectNumber}'), mode = 'w') as f:
        f.write(additionalComments)
    return


# exit screen thanking the participant
def nonConsentScreen(win):
    pg.mouse.set_visible(False)
    win.fill(backgroundColor)
    multiLineMessage(nonConsentText, mediumFont, win)
    pg.display.flip()
    waitKey(pg.K_SPACE)
    pg.quit()
    sys.exit()


# contains questionnaire questions and displays questionnaire to the subject
def consentScreen(subjectName, subjectNumber, subjectEmail, experimenterName, win):
    index = 0
    email_consent = False  # Initialize email consent variable
    while True:
        pg.mouse.set_visible(False)

        if index == 0:
            pg.event.clear()
            running = True
            while running:
                win.fill(backgroundColor)
                multiLineMessage(studyInfoText, mediumFont, win)
                pg.display.flip()
                for event in pg.event.get():
                    if event.type == pg.KEYDOWN:
                        if event.key == pg.K_ESCAPE:
                            pg.quit()
                            sys.exit()
                        elif event.key == pg.K_RIGHT:
                            index += 1
                            running = False

        elif index == 1:
            pg.event.clear()
            running = True
            while running:
                win.fill(backgroundColor)
                multiLineMessage(risksAndBenefitsText, mediumFont, win)
                pg.display.flip()
                for event in pg.event.get():
                    if event.type == pg.KEYDOWN:
                        if event.key == pg.K_ESCAPE:
                            pg.quit()
                            sys.exit()
                        elif event.key == pg.K_RIGHT:
                            index += 1
                            running = False
                        elif event.key == pg.K_LEFT:
                            index -= 1
                            running = False

        elif index == 2:
            running = True
            while running:
                win.fill(backgroundColor)
                multiLineMessage(confidentialityText, mediumFont, win)
                pg.display.flip()
                for event in pg.event.get():
                    if event.type == pg.KEYDOWN:
                        if event.key == pg.K_ESCAPE:
                            pg.quit()
                            sys.exit()
                        elif event.key == pg.K_RIGHT:
                            index += 1
                            running = False
                        elif event.key == pg.K_LEFT:
                            index -= 1
                            running = False
                    
        elif index == 3:
            running = True
            while running:
                win.fill(backgroundColor)
                multiLineMessage(contactsAndQuestionsText, mediumFont, win)
                pg.display.flip()
                for event in pg.event.get():
                    if event.type == pg.KEYDOWN:
                        if event.key == pg.K_ESCAPE:
                            pg.quit()
                            sys.exit()
                        elif event.key == pg.K_RIGHT:
                            index += 1
                            running = False
                        elif event.key == pg.K_LEFT:
                            index -= 1
                            running = False

        elif index == 4:
            pg.mouse.set_visible(True)
            # variables to hold all of the questions and their associated response options
            questions = []

            # question 1 text and response options
            question1 = 'By clicking “I agree” below, you confirm that you have read the consent form, are at least 18 years old, and agree to participate in the research. We will provide you a paper copy of this consent form upon completion of the study. By selecting “I do NOT agree” you will not be able to participate in this research and we thank you for your consideration. You may use the arrow keys to review the information in this consent form before making a decision.'
            ResponseOptions1 = ['I agree to participate in the research', 'I do NOT agree to participate in the research ']
            questions.append([question1] + ResponseOptions1)

            submitButton = Button('submit', 'tellegen', 'Submit', -1, 0) # submit button
            responses = [] # for storing answers to each question

            # iterate over each question and display to user
            for i, question in enumerate(questions):

                response = None
                running = True

                current_w, current_h = _current_window_size(win)
                # Keep the question text in the top portion so options don't get pushed into a new column
                yPos = multiLineMessage(question[0], mediumFont, win, yMax=0.60 * current_h)

                # create all of the options for this particular questions
                buttons = [submitButton]
                for opt_i, question_option in enumerate(question[1:], start=1):
                    buttons.append(Button('option', 'binary', question_option, opt_i, yPos))

                while response == None and running:
                    win.fill(backgroundColor)
                    for event in pg.event.get():
                        if event.type == pg.KEYDOWN:
                            if event.key == pg.K_ESCAPE: # escape will exit the study
                                pg.quit()
                                sys.exit()
                            if event.key == pg.K_LEFT:
                                index -= 1
                                running = False
                        elif event.type == pg.MOUSEBUTTONUP:
                            for i, button in enumerate(buttons):
                                if (button.coords[0] <= pg.mouse.get_pos()[0] <= button.coords[0] + button.coords[2]) \
                                    and (button.coords[1] <= pg.mouse.get_pos()[1] <= button.coords[1] + button.coords[3]):
                                    response = button.handleClick(buttons)
                        pg.event.clear()

                    current_w, current_h = _current_window_size(win)
                    multiLineMessage(question[0], mediumFont, win, yMax=0.60 * current_h)

                    # draw the submit button and the checkboxes for this questions
                    submitButton.draw(win)
                    for i, button in enumerate(buttons): 
                        button.draw(win)
                    pg.display.flip() 
                
                # add the user's response to the list of responses
                if response:
                    responses.append(response)
            if len(responses) != 0:  
                if 'I agree' in responses[0]:
                    consented = True
                    index += 1  # Move to email consent screen
                else:
                    consented = False
                    signature = ''
                    email_consent = False
                    break
            else:
                break

        elif index == 5:
            # Email consent screen
            pg.mouse.set_visible(True)
            questions = []

            # Email consent question
            email_question = 'May we use your email address to contact you about future research studies?\n\nThis is optional and will not affect your participation or compensation in the current study. You can withdraw this permission at any time by contacting the researchers.\n\nBy selecting "Yes", you agree to be contacted about future research opportunities. By selecting "No", we will not contact you for future studies.'
            email_options = ['Yes, you may contact me about future studies', 'No, please do not contact me about future studies']
            questions.append([email_question] + email_options)

            submitButton = Button('submit', 'tellegen', 'Submit', -1, 0)
            email_responses = []

            # iterate over each question and display to user
            for i, question in enumerate(questions):

                response = None
                running = True

                current_w, current_h = _current_window_size(win)
                yPos = multiLineMessage(question[0], mediumFont, win, yMax=0.60 * current_h)

                # create all of the options for this particular questions
                buttons = [submitButton]
                for opt_i, question_option in enumerate(question[1:], start=1):
                    buttons.append(Button('option', 'binary', question_option, opt_i, yPos))

                while response == None and running:
                    win.fill(backgroundColor)
                    for event in pg.event.get():
                        if event.type == pg.KEYDOWN:
                            if event.key == pg.K_ESCAPE:
                                pg.quit()
                                sys.exit()
                            if event.key == pg.K_LEFT:
                                index -= 1
                                running = False
                        elif event.type == pg.MOUSEBUTTONUP:
                            for i, button in enumerate(buttons):
                                if (button.coords[0] <= pg.mouse.get_pos()[0] <= button.coords[0] + button.coords[2]) \
                                    and (button.coords[1] <= pg.mouse.get_pos()[1] <= button.coords[1] + button.coords[3]):
                                    response = button.handleClick(buttons)
                        pg.event.clear()

                    current_w, current_h = _current_window_size(win)
                    multiLineMessage(question[0], mediumFont, win, yMax=0.60 * current_h)

                    # draw the submit button and the checkboxes for this questions
                    submitButton.draw(win)
                    for i, button in enumerate(buttons): 
                        button.draw(win)
                    pg.display.flip() 
                
                # add the user's response to the list of responses
                if response:
                    email_responses.append(response)
            
            if len(email_responses) != 0:  
                if 'Yes' in email_responses[0]:
                    email_consent = True
                else:
                    email_consent = False
                
                # Get signature after both consents are completed
                pg.mouse.set_visible(False)
                signature = getSubjectInfo('Signature', win)
                break
    
    # Create a timezone object for Central Time
    central_tz = pytz.timezone('America/Chicago')

    # Get the current time in UTC
    current_utc = datetime.now(pytz.utc)

    # Convert the current UTC time to Central Time
    current_central = current_utc.astimezone(central_tz)

    # Format the date and time in a specific format e.g., YYYY-MM-DD HH:MM:SS
    formatted_date = current_central.strftime('%Y-%m-%d %H:%M:%S')
    # write all of the responses to a csv file with the questionnaire's name as the file name. 
    with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'consentInfo_{subjectNumber}.csv'), mode = 'w', newline = '') as f:
        writer = csv.writer(f)
        writer.writerow(['Subject Number', 'Subject Name', 'Subject Email', 'Experimenter Name', 'Consented', 'Email Consent', 'Date'])
        if not consented:
            writer.writerow([subjectNumber, subjectName, subjectEmail, experimenterName, str(consented), str(email_consent), formatted_date])
        else:
            writer.writerow([subjectNumber, signature, subjectEmail, experimenterName, str(consented), str(email_consent), formatted_date])
    return consented

# =======================================================================
# =======================================================================

def concatenate_wavs(prefix_path, stimulus_path, add_gap=True, gap_ms=120, fs_out: int = 44100):
    """Concatenate two WAVs as cached mono int16 arrays (optionally with a silence gap)."""
    key = (os.path.abspath(prefix_path), os.path.abspath(stimulus_path), bool(add_gap), int(gap_ms), int(fs_out))
    cached = _CONCAT_CACHE.get(key)
    if cached is not None:
        return cached

    prefix_pcm = get_pcm16_mono(prefix_path, fs_out)
    stim_pcm = get_pcm16_mono(stimulus_path, fs_out)

    if add_gap and gap_ms > 0:
        gap_samples = int(round(fs_out * (gap_ms / 1000.0)))
        silence = np.zeros((gap_samples,), dtype=np.int16)
        out = np.concatenate([prefix_pcm, silence, stim_pcm])
    else:
        out = np.concatenate([prefix_pcm, stim_pcm])

    _CONCAT_CACHE[key] = out
    return out
    
def selectStimulus(targets, distractors, prefix_wav, fs_out: int = 44100):
    # select a stimulus and remove it from its associated list
    masterList = targets + distractors
    stimulus = choice(masterList)

    if stimulus in targets:
        stimulusType = 'target'
        targets.remove(stimulus)
    else:
        stimulusType = 'distractor'
        distractors.remove(stimulus)

    # If prefix_wav is provided, concatenate; otherwise use stimulus as-is.
    if prefix_wav:
        sound = concatenate_wavs(prefix_wav, stimulus, add_gap=False, fs_out=fs_out)
    else:
        sound = get_pcm16_mono(stimulus, fs_out)

    # get filename without extension
    filename = os.path.splitext(os.path.basename(stimulus))[0]

    return sound, filename, stimulusType


# Audio playback and replay functionality
# =======================================================================
def wait_ms(ms: int):
    end = pg.time.get_ticks() + ms
    while pg.time.get_ticks() < end:
        pg.event.pump()
        pg.time.delay(2)
def playAudioStimulus(audio_engine, pcm16):
    duration_ms = audio_engine.play(pcm16)
    return duration_ms

def createPlayButton(win):
    """Create a play button"""
    current_w, current_h = _current_window_size(win)

    # Make button size proportional to current window
    button_width = int(0.18 * current_w)
    button_height = int(0.08 * current_h)
    button_x = (current_w - button_width) // 2
    button_y = (current_h - button_height) // 2 + int(0.08 * current_h)
    
    button_rect = pg.Rect(button_x, button_y, button_width, button_height)
    return button_rect

def drawPlayButton(win, button_rect, enabled=True, audio_played=False, can_play=True):
    """Draw the play button"""
    if not can_play:
        color = [c//2 for c in BLUE]  # Dimmed blue when waiting for audio
        text_color = GRAY
    elif not enabled:
        color = GRAY
        text_color = BLACK
    else:
        color = BLUE
        text_color = WHITE
    
    pg.draw.rect(win, color, button_rect)
    pg.draw.rect(win, BLACK, button_rect, 3)  # Border
    
    _, current_h = _current_window_size(win)
    font = pg.font.SysFont("times new roman", max(18, current_h // 35))
    text = "Play Audio"
    
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=button_rect.center)
    win.blit(text_surface, text_rect)

def drawAudioInterface(win, play_count, max_plays, audio_played=False, can_play=True, can_respond=True, block_name=None):
    """Draw the audio interface with instructions and play button"""
    win.fill(backgroundColor)

    current_w, current_h = _current_window_size(win)
    
    # Block-specific trial instructions (editable in constants.py)
    if block_name == 'imagined_sentence':
        instructions = list(trialInstructions_imagined_sentence)
    else:
        instructions = list(trialInstructions_full_sentence)

    # Draw play button first so we can avoid overlapping it with text
    button_rect = createPlayButton(win)
    enabled = play_count < max_plays and can_play
    drawPlayButton(win, button_rect, enabled, audio_played, can_play)

    # Lay out instructions above the play button
    y_pos = current_h // 10
    font = pg.font.SysFont("times new roman", max(22, current_h // 28))
    line_step = max(22, font.get_linesize())
    paragraph_step = max(26, current_h // 18)
    max_text_y = max(0, button_rect.top - int(0.05 * current_h))

    max_text_width = int(0.90 * current_w)

    for instruction in instructions:
        if y_pos + line_step > max_text_y:
            break
        if not instruction:
            y_pos += paragraph_step
            continue

        for wrapped_line in _wrap_text_to_width(font, instruction, max_text_width):
            if y_pos + line_step > max_text_y:
                break
            if wrapped_line:
                text_surface = font.render(wrapped_line, True, BLACK)
                text_rect = text_surface.get_rect(center=(current_w // 2, y_pos))
                win.blit(text_surface, text_rect)
            y_pos += line_step
        y_pos += max(0, paragraph_step - line_step)

    # Draw play-count separately so it never overlaps the button
    # counter_font = pg.font.SysFont("times new roman", max(18, current_h // 35))
    # # counter_surface = counter_font.render(f"Plays used: {play_count}/{max_plays}", True, BLACK)
    # counter_y = button_rect.top - int(0.03 * current_h)
    # if counter_y < int(0.02 * current_h):
    #     counter_y = int(0.02 * current_h)
    # # counter_rect = counter_surface.get_rect(center=(current_w // 2, counter_y))
    # # win.blit(counter_surface, counter_rect)
    
    return button_rect


def showTargetFamiliarization(win, subjectNumber, saveFolder, session_number, block_name, audio_engine):
    """
    Show the target familiarization screen.
    Participants must play the target sound a fixed number of times before they can continue.
    
    Args:
        win: pygame window
        subjectNumber: subject identifier
        saveFolder: folder to save data
        session_number: which time the user is seeing this screen (1, 2, 3, etc.)
    """
    pg.mouse.set_visible(True)
    
    # Load the block-appropriate target sound
    audio_stimuli_dir = os.path.join(os.path.dirname(__file__), 'audio_stimuli')
    
    # Both blocks do the same thing but they were previously different that is why an if/else exists here
    if block_name == 'imagined_sentence':
        actual_target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    else:
        actual_target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    fs_out = int(audio_engine.fs)
    actual_target_pcm = get_pcm16_mono(actual_target_path, fs_out)
    
    required_plays = int(FAMILIARIZATION_MAX_PLAYS)
    play_count = 0
    # Add timing variables for delay system
    last_audio_start = 0
    audio_duration = int(round(1000.0 * (actual_target_pcm.shape[0] / fs_out)))
    
    # Create play button (larger for this screen)
    button_width = int(0.2 * winWidth)  # 20% of screen width
    button_height = int(0.08 * winHeight)  # 8% of screen height
    
    # Create continue button
    continue_button_width = int(0.15 * winWidth)
    continue_button_height = int(0.06 * winHeight)
    
    while True:
        win.fill(backgroundColor)
        
        # Check if play button can be clicked (timing system)
        current_time = pg.time.get_ticks()
        time_since_last_play = current_time - last_audio_start
        can_play = (last_audio_start == 0) or (time_since_last_play >= audio_duration + 250)

        audio_still_playing = (last_audio_start != 0) and (time_since_last_play < audio_duration)
        continue_enabled = (play_count >= required_plays) and (not audio_still_playing)
        instructions = [
                "Target Sound Familiarization",
                "",
                "This is the TARGET sound you should listen for in the upcoming block.",
                f"You must play it {required_plays} time(s) before you can continue.",
                "Click 'Play Target Sound' to hear the sound.",
                "Click 'Continue' after you have finished all required plays.",
            ]
        # # Display instructions
        # if block_name == "full_sentence":
        #     instructions = [
        #         "Target Sound Familiarization",
        #         "",
        #         "This is the TARGET sound you should listen for in the upcoming block.",
        #         f"You must play it {required_plays} time(s) before you can continue.",
        #         "Click 'Play Target Sound' to hear the sound.",
        #         "Click 'Continue' after you have finished all required plays.",
        #     ]
        # else:
        #     instructions = [
        #         "Target Sound Familiarization",
        #         "",
        #         "This is the TARGET sound you should listen for in the upcoming block.",
        #         f"You must play it {required_plays} time(s) before you can continue.",
        #         "Imagine the sentence EVERY TIME before playing the audio sample.",
        #         "Do NOT say the sentence out loud, under your breath, or mouth it.",
        #         "Click 'Play Target Sound' to hear the sound.",
        #         "Click 'Continue' after you have finished all required plays.",
        #     ]
        
        y_pos = winHeight // 8
        font = pg.font.SysFont("times new roman", mediumFont)
        
        for instruction in instructions:
            if instruction:
                text_surface = font.render(instruction, True, BLACK)
                text_rect = text_surface.get_rect(center=(winWidth // 2, y_pos))
                win.blit(text_surface, text_rect)
            y_pos += (mediumFont + 10)
        

        play_y = int(y_pos + 0.25 * (winHeight - y_pos)) - button_height // 2
        cont_y = int(y_pos + 0.50 * (winHeight - y_pos)) - continue_button_height // 2

        play_button_rect = pg.Rect((winWidth - button_width) // 2, play_y, button_width, button_height)
        continue_button_rect = pg.Rect((winWidth - continue_button_width) // 2, cont_y, continue_button_width, continue_button_height)
        
        can_click_play = can_play and (play_count < required_plays)

        if can_click_play:
            play_button_color = BLUE
            play_text_color = WHITE
            play_text_content = "Play Target Sound"
        elif play_count >= required_plays:
            play_button_color = GRAY
            play_text_color = BLACK
            play_text_content = "Max Plays Reached"
        else:
            play_button_color = [c//2 for c in BLUE]
            play_text_color = GRAY
            play_text_content = "Play Target Sound"
        
        pg.draw.rect(win, play_button_color, play_button_rect)
        pg.draw.rect(win, BLACK, play_button_rect, 3)
        
        # Draw continue button (green only after all required plays)
        continue_color = GREEN if continue_enabled else GRAY
        pg.draw.rect(win, continue_color, continue_button_rect)
        pg.draw.rect(win, BLACK, continue_button_rect, 3)
        
        # Button labels
        font = pg.font.SysFont("times new roman", smallFont)
        play_text = font.render(play_text_content, True, play_text_color)
        continue_text = font.render("Continue", True, BLACK if continue_enabled else WHITE)
        
        win.blit(play_text, play_text.get_rect(center=play_button_rect.center))
        win.blit(continue_text, continue_text.get_rect(center=continue_button_rect.center))

        # Progress indicator
        counter_font = pg.font.SysFont("times new roman", max(18, winHeight // 35))
        counter_surface = counter_font.render(f"Plays: {play_count}/{required_plays}", True, BLACK)
        counter_y = play_button_rect.top - int(0.03 * winHeight)
        if counter_y < int(0.02 * winHeight):
            counter_y = int(0.02 * winHeight)
        win.blit(counter_surface, counter_surface.get_rect(center=(winWidth // 2, counter_y)))
        
        pg.display.flip()
        
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                mouse_pos = pg.mouse.get_pos()

                current_time = pg.time.get_ticks()
                time_since_last_play = current_time - last_audio_start
                audio_still_playing = (last_audio_start != 0) and (time_since_last_play < audio_duration)

                if play_button_rect.collidepoint(mouse_pos) and can_click_play:
                    audio_duration = playAudioStimulus(audio_engine, actual_target_pcm)
                    last_audio_start = current_time
                    play_count += 1
                elif continue_button_rect.collidepoint(mouse_pos) and (play_count >= required_plays) and not audio_still_playing:
                    # Save data and return
                    saveTargetFamiliarizationData(subjectNumber, saveFolder, session_number, play_count, block_name)
                    return


def saveTargetFamiliarizationData(subjectNumber, saveFolder, session_number, play_count, block_name):
    """
    Save the target familiarization data to a CSV file.
    
    Args:
        subjectNumber: subject identifier
        saveFolder: folder to save data
        session_number: which session this was (1st time, 2nd time, etc.)
        play_count: how many times they played the target sound
    """
    import csv
    from datetime import datetime
    
    # Create filename
    filePath = os.path.join(saveFolder, f'target_familiarization_{subjectNumber}.csv')
    
    # Prepare data
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = ['Subject Number', 'Session Number', 'Block Name', 'Play Count', 'Timestamp']
    data = [subjectNumber, session_number, block_name, play_count, timestamp]

    # Write to file
    try:
        # Check if file exists to determine if we need to write header
        file_exists = os.path.exists(filePath)
        
        with open(filePath, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(header)
            writer.writerow(data)
    except Exception as e:
        print(f"Error saving target familiarization data: {e}")


def showPeriodicReminder(win, subjectNumber, saveFolder, trial_number, block_name, audio_engine):
    """
    Show a periodic reminder screen that appears every N trials to let users replay the target.
    Similar to target familiarization but with limited plays.
    
    Args:
        win: pygame window
        subjectNumber: subject identifier
        saveFolder: folder to save data
        trial_number: which trial number this reminder appeared on (within the block)
        block_name: name of the current block (e.g., 'high_frequency', 'low_frequency')
    """
    pg.mouse.set_visible(True)
    
    # Load the block-appropriate target sound
    audio_stimuli_dir = os.path.join(os.path.dirname(__file__), 'audio_stimuli')
    # Both blocks do the same thing but they were previously different that is why an if/else exists here
    if block_name == 'imagined_sentence':
        actual_target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    else:
        actual_target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    fs_out = int(audio_engine.fs)
    actual_target_pcm = get_pcm16_mono(actual_target_path, fs_out)
    
    required_plays = int(REMINDER_MAX_PLAYS)
    play_count = 0
    # Add timing variables for delay system
    last_audio_start = 0
    audio_duration = int(round(1000.0 * (actual_target_pcm.shape[0] / fs_out)))
    
    # Create play button (larger for this screen)
    button_width = int(0.2 * winWidth)  # 20% of screen width
    button_height = int(0.08 * winHeight)  # 8% of screen height
    
    # Create continue button
    continue_button_width = int(0.15 * winWidth)
    continue_button_height = int(0.06 * winHeight)

    while True:
        win.fill(backgroundColor)
        
        # Check if play button can be clicked (timing system)
        current_time = pg.time.get_ticks()
        time_since_last_play = current_time - last_audio_start
        can_play = (last_audio_start == 0) or (time_since_last_play >= audio_duration + 350)

        audio_still_playing = (last_audio_start != 0) and (time_since_last_play < audio_duration)
        continue_enabled = (play_count >= required_plays) and (not audio_still_playing)
        
        instructions = [
                "Target Sound Reminder",
                "",
                f"Here's a reminder of the \"Wall\" that you are searching for.",
                "Click 'Play Target Sound' to hear the sound.",
                f"You must play it {required_plays} times before you can continue.",
                "Click 'Continue' after you have finished all required plays.",
                "",
                f"Plays: {play_count}/{required_plays}",
            ]
            
        # Display instructions
        if block_name == "full_sentence":
            instructions = [
                "Target Sound Reminder",
                "",
                f"Here's a reminder of the \"Wall\" that you are searching for.",
                "Click 'Play Target Sound' to hear the sound.",
                f"You must play it {required_plays} times before you can continue.",
                "Click 'Continue' after you have finished all required plays.",
                "",
                f"Plays: {play_count}/{required_plays}",
            ]
        else:
            instructions = [
                "Target Sound Reminder",
                "",
                f"Here's a reminder of the \"Wall\" that you are searching for.",
                "Imagine the sentence EVERY TIME before playing the audio sample.",
                "Do NOT say the sentence out loud, under your breath, or mouth it.",
                "Click 'Play Target Sound' to hear the sound.",
                f"You must play it {required_plays} times before you can continue.",
                "Click 'Continue' after you have finished all required plays.",
                "",
                f"Plays: {play_count}/{required_plays}",
            ]
        
        y_pos = winHeight // 8
        font = pg.font.SysFont("times new roman", mediumFont)
        
        for instruction in instructions:
            if instruction:
                text_surface = font.render(instruction, True, BLACK)
                text_rect = text_surface.get_rect(center=(winWidth // 2, y_pos))
                win.blit(text_surface, text_rect)
            y_pos += mediumFont
        
        # Draw play button with timing consideration and max plays limit
        can_click = can_play and (play_count < required_plays)
        
        if can_click:
            play_button_color = BLUE
            play_text_color = WHITE
        elif play_count >= required_plays:
            play_button_color = GRAY
            play_text_color = BLACK
        else:  # waiting for audio to finish
            play_button_color = [c//2 for c in BLUE]  # Dimmed blue
            play_text_color = GRAY

        play_y = int(y_pos + 0.25 * (winHeight - y_pos)) - button_height // 2
        cont_y = int(y_pos + 0.50 * (winHeight - y_pos)) - continue_button_height // 2

        play_button_rect = pg.Rect((winWidth - button_width) // 2, play_y, button_width, button_height)
        continue_button_rect = pg.Rect((winWidth - continue_button_width) // 2, cont_y, continue_button_width, continue_button_height)

        pg.draw.rect(win, play_button_color, play_button_rect)
        pg.draw.rect(win, BLACK, play_button_rect, 3)
        
        # Draw continue button (only available after all required plays)
        continue_color = GREEN if continue_enabled else GRAY
        pg.draw.rect(win, continue_color, continue_button_rect)
        pg.draw.rect(win, BLACK, continue_button_rect, 3)
        
        # Button labels
        font = pg.font.SysFont("times new roman", smallFont)
        if play_count >= required_plays:
            play_text_content = "Max Plays Reached"
        else:
            play_text_content = "Play Target Sound"
        
        play_text = font.render(play_text_content, True, play_text_color)
        continue_text = font.render("Continue", True, BLACK if continue_enabled else WHITE)
        
        win.blit(play_text, play_text.get_rect(center=play_button_rect.center))
        win.blit(continue_text, continue_text.get_rect(center=continue_button_rect.center))
        
        pg.display.flip()
        
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                mouse_pos = pg.mouse.get_pos()
                current_time = pg.time.get_ticks()
                time_since_last_play = current_time - last_audio_start
                audio_still_playing = (last_audio_start != 0) and (time_since_last_play < audio_duration)

                if play_button_rect.collidepoint(mouse_pos) and can_click:
                    audio_duration = playAudioStimulus(audio_engine, actual_target_pcm)
                    last_audio_start = current_time
                    play_count += 1
                elif continue_button_rect.collidepoint(mouse_pos) and (play_count >= required_plays) and not audio_still_playing:
                    # Save data and return
                    savePeriodicReminderData(subjectNumber, saveFolder, trial_number, play_count, block_name)
                    return


def savePeriodicReminderData(subjectNumber, saveFolder, trial_number, play_count, block_name):
    """
    Save the periodic reminder data to a block-specific CSV file.
    
    Args:
        subjectNumber: subject identifier
        saveFolder: folder to save data
        trial_number: which trial number this reminder appeared on (within the block)
        play_count: how many times they played the target sound
        block_name: name of the current block (e.g., 'high_frequency', 'low_frequency')
    """
    import csv
    from datetime import datetime
    
    # Create block-specific filename
    filePath = os.path.join(saveFolder, f'periodic_reminders_{block_name}_{subjectNumber}.csv')
    
    # Prepare data
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = ['Subject Number', 'Block Name', 'Trial Number (Block)', 'Play Count', 'Timestamp']
    data = [subjectNumber, block_name, trial_number, play_count, timestamp]
    
    # Write to file
    try:
        # Check if file exists to determine if we need to write header
        file_exists = os.path.exists(filePath)
        
        with open(filePath, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(header)
            writer.writerow(data)
    except Exception as e:
        print(f"Error saving periodic reminder data: {e}")


def showAudioLevelTest(win, audio_engine):
    """
    Show audio level testing screen for the experimenter to normalize audio levels.
    Allows playing white noise and target wall sounds as many times as needed.
    Also includes continuous background noise with start/stop controls.
    
    Args:
        win: pygame window
    """
    pg.mouse.set_visible(True)
    
    # Load audio files
    audio_stimuli_dir = os.path.join(os.path.dirname(__file__), 'audio_stimuli')
    
    fs_out = int(audio_engine.fs)

    target_path = os.path.join(audio_stimuli_dir, 'fullsentence.wav')
    background_noise_path = os.path.join(audio_stimuli_dir, '60s_background_noise.wav')

    target_pcm = get_pcm16_mono(target_path, fs_out)
    background_pcm = get_pcm16_mono(background_noise_path, fs_out)

    background_playing = False
    target_playing = False
    
    while True:
        current_w, current_h = _current_window_size(win)

        # Create buttons - continuous playback controls (relative to current window)
        button_width = int(0.2 * current_w)
        button_height = int(0.08 * current_h)

        background_button_rect = pg.Rect(current_w // 4 - button_width // 2, int(0.5 * current_h), button_width, button_height)
        target_button_rect = pg.Rect(3 * current_w // 4 - button_width // 2, int(0.5 * current_h), button_width, button_height)

        continue_button_width = int(0.15 * current_w)
        continue_button_height = int(0.06 * current_h)
        continue_button_rect = pg.Rect((current_w - continue_button_width) // 2, int(0.8 * current_h), continue_button_width, continue_button_height)

        win.fill(backgroundColor)
        
        # Display instructions
        instructions = [
            "Audio Level Testing - For Experimenter",
            "",
            "Use this screen to normalize audio levels before starting the experiment.",
            "Adjust system volume so both sounds are at comfortable levels.",
            "When audio levels are properly set, click 'Continue' to proceed."
        ]
        
        y_pos = current_h // 8
        font = pg.font.SysFont("times new roman", max(18, current_h // 25))
        
        for instruction in instructions:
            if instruction:
                text_surface = font.render(instruction, True, BLACK)
                text_rect = text_surface.get_rect(center=(current_w // 2, y_pos))
                win.blit(text_surface, text_rect)
            y_pos += max(28, current_h // 22)
        
        # Draw buttons - both are start/stop toggles
        
        # Background noise button color based on state
        if background_playing:
            background_color = RED  # Red when playing (shows "Stop")
            background_text_color = WHITE
        else:
            background_color = GREEN  # Green when stopped (shows "Start")
            background_text_color = BLACK
            
        # Target button color based on state
        if target_playing:
            target_color = RED  # Red when playing (shows "Stop")
            target_text_color = WHITE
        else:
            target_color = GREEN  # Green when stopped (shows "Start")
            target_text_color = BLACK
        
        # Draw background noise button
        pg.draw.rect(win, background_color, background_button_rect)
        pg.draw.rect(win, BLACK, background_button_rect, 3)
        
        # Draw target button
        pg.draw.rect(win, target_color, target_button_rect)
        pg.draw.rect(win, BLACK, target_button_rect, 3)
        
        # Draw continue button (always blue)
        pg.draw.rect(win, BLUE, continue_button_rect)
        pg.draw.rect(win, BLACK, continue_button_rect, 3)
        
        # Button labels
        font = pg.font.SysFont("times new roman", max(14, current_h // 45))
        
        # Background noise button text changes based on state
        background_text_content = "Stop Background" if background_playing else "Start Background"
        background_text = font.render(background_text_content, True, background_text_color)
        
        # Target button text changes based on state
        target_text_content = "Stop Target Wall" if target_playing else "Start Target Wall"
        target_text = font.render(target_text_content, True, target_text_color)
        
        continue_text = font.render("Continue", True, WHITE)
        
        win.blit(background_text, background_text.get_rect(center=background_button_rect.center))
        win.blit(target_text, target_text.get_rect(center=target_button_rect.center))
        win.blit(continue_text, continue_text.get_rect(center=continue_button_rect.center))
        
        pg.display.flip()
        
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()
            elif event.type == pg.MOUSEBUTTONDOWN:
                mouse_pos = pg.mouse.get_pos()
                
                # Handle background noise start/stop
                if background_button_rect.collidepoint(mouse_pos):
                    if background_playing:
                        audio_engine.stop_loop('background')
                        background_playing = False
                    else:
                        audio_engine.start_loop('background', background_pcm)
                        background_playing = True
                
                # Handle target wall start/stop
                elif target_button_rect.collidepoint(mouse_pos):
                    if target_playing:
                        audio_engine.stop_loop('target')
                        target_playing = False
                    else:
                        audio_engine.start_loop('target', target_pcm)
                        target_playing = True
                
                elif continue_button_rect.collidepoint(mouse_pos):
                    # Stop all audio if playing when exiting
                    if background_playing:
                        audio_engine.stop_loop('background')
                    if target_playing:
                        audio_engine.stop_loop('target')
                    return

