import os
import sys
import csv
from random import choice
from scipy.stats import norm
import pygame as pg
import pytz
from datetime import datetime
from constants import *


imageWidth, imageHeight = 50, 50
imageSize = imageWidth * imageHeight

# class for the buttons the user will see
class Button:

    # initializes an instance of a button
    def __init__(self, buttonType, questionnaireName, text, i, yPosQuestion):

         # creates a box to click and text for questionnaire options
        if buttonType == 'option':
            self.fontSize = mediumFont
            if questionnaireName == 'tellegen':
                scalar = 1.75
            elif questionnaireName == 'launay':
                scalar = 1.4
            elif questionnaireName == 'dissociative':
                scalar = 1.5
            spacing = scalar * i * self.fontSize 
            buffer = winHeight // 20
            maxY = (0.85 * winHeight) - self.fontSize
            
            # Make option button size proportional to screen
            button_size = int(0.015 * min(winWidth, winHeight))  # 1.5% of smaller screen dimension
            button_size = max(button_size, self.fontSize)  # Ensure it's at least as big as font
            
            self.coords = ((0.05 * winWidth) + (0.45 * winWidth) * ((yPosQuestion + spacing + buffer) // maxY), 
                           yPosQuestion + buffer + (spacing % (maxY - (yPosQuestion + buffer))), 
                           button_size, 
                           button_size)
            self.text_x = self.coords[0] + 1.5 * button_size
            self.text_y = self.coords[1] - 0.1 * button_size
            
        else: # creates the submit button so the user may submit their response
            self.fontSize = int(0.85 * mediumFont)
            
            # Calculate text dimensions for responsive sizing
            font = pg.font.SysFont("times new roman", self.fontSize)
            text_surface = font.render(text, True, BLACK)
            text_width, text_height = text_surface.get_size()
            
            # Make button size proportional to screen and text
            padding_x = int(0.02 * winWidth)  # 2% of screen width padding
            padding_y = int(0.01 * winHeight)  # 1% of screen height padding
            button_width = text_width + (2 * padding_x)
            button_height = text_height + (2 * padding_y)
            
            # Ensure minimum size (proportional to screen)
            min_width = int(0.08 * winWidth)
            min_height = int(0.04 * winHeight)
            button_width = max(button_width, min_width)
            button_height = max(button_height, min_height)
            
            # Center the button horizontally, position vertically at 85% of screen height
            button_x = (winWidth - button_width) // 2
            button_y = int(0.85 * winHeight)
            
            self.coords = (button_x, button_y, button_width, button_height)
            # Text positioning will be handled by centering in draw method
            self.text_x = 0.46 * winWidth  # Keep for compatibility, but draw() will center
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

# function to draw/fit a multiline message to the screen
def multiLineMessage(text, textsize, win, xPos_start = 0.05 * winWidth, yPos_start = 0.05 * winHeight, xMax = 0.95 * winWidth, yMax = 0.95 * winHeight):

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
    if requestType == 'selfReflect_changes' or requestType == 'selfReflect_explanation':
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
        if requestType == 'signature':
            text = "Please type your name to confirm that you consent to participate in this study. Press Enter or Return to submit.\n\n"
        elif requestType == 'selfReflect_explanation':
            text = 'During the experiment, how did you decide whether or not the word "Wall" was in each of the stimuli? What were you thinking about or considering as you made that decision?\n'
        elif requestType == 'selfReflect_changes':
            text = 'Did your methodology change or evolve over the course of the experiment?\n'
        elif requestType == 'Additional Comments':
            text = 'Please provide any additional comments you may have about the experiment below. If you have no additional comments, simply press Enter or Return to continue.\n'
        else:
            text = "Please enter the requested information. Then press Enter or Return to continue. Press ESC to exit or inform the observer of your decision. \n\n"
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

    # list of file names as paths for high frequency (44khz) audio
    high_frequency_targets = [os.path.join(stimuliDir, '44khz', 'targets', fileName) 
                             for fileName in os.listdir(os.path.join(stimuliDir, '44khz', 'targets'))]
    high_frequency_distractors = [os.path.join(stimuliDir, '44khz', 'distractors', fileName) 
                                 for fileName in os.listdir(os.path.join(stimuliDir, '44khz', 'distractors'))]

    # list of file names as paths for low frequency (8khz) audio
    low_frequency_targets = [os.path.join(stimuliDir, '8khz', 'targets', fileName) 
                            for fileName in os.listdir(os.path.join(stimuliDir, '8khz', 'targets'))]
    low_frequency_distractors = [os.path.join(stimuliDir, '8khz', 'distractors', fileName) 
                                for fileName in os.listdir(os.path.join(stimuliDir, '8khz', 'distractors'))]

    return high_frequency_targets, high_frequency_distractors, low_frequency_targets, low_frequency_distractors 



# This code is for showing various message screens (e.g. experiment explanation)
# and functions that display images
# =======================================================================
# =======================================================================

# shows the example audio stimuli
def showExamples(win, text = ''):
    pg.mouse.set_visible(True)
    
    # Use first audio file from each category as examples
    audio_stimuli_dir = os.path.join(os.path.dirname(__file__), 'audio_stimuli')
    
    # Get example files (first target and first distractor from 44khz)
    target_files = os.listdir(os.path.join(audio_stimuli_dir, '44khz', 'targets'))
    distractor_files = os.listdir(os.path.join(audio_stimuli_dir, '44khz', 'distractors'))
    
    if target_files and distractor_files:
        # Example target (highly correlated example)
        target_example_path = os.path.join(audio_stimuli_dir, '44khz', 'targets', target_files[0])
        # Example distractor
        distractor_example_path = os.path.join(audio_stimuli_dir, '44khz', 'distractors', distractor_files[0])
        # Actual target (the main target participants should identify)
        actual_target_path = os.path.join(audio_stimuli_dir, 'target.wav')
        
        target_sound = pg.mixer.Sound(target_example_path)
        distractor_sound = pg.mixer.Sound(distractor_example_path)
        actual_target_sound = pg.mixer.Sound(actual_target_path)
        
        # Create three buttons - spread horizontally with actual target in center
        # Make button sizes proportional to screen
        button_width = int(0.15 * winWidth)  # 15% of screen width
        button_height = int(0.06 * winHeight)  # 6% of screen height
        button_y = winHeight // 2 - button_height // 2
        
        # Left: Sample Target (Green)
        sample_target_button_rect = pg.Rect(winWidth // 6 - button_width//2, button_y, button_width, button_height)
        # Center: Actual Target (Blue)
        actual_target_button_rect = pg.Rect(winWidth // 2 - button_width//2, button_y, button_width, button_height)
        # Right: Sample Distractor (Red)
        sample_distractor_button_rect = pg.Rect(5 * winWidth // 6 - button_width//2, button_y, button_width, button_height)
        
        # Continue button (colored) - also make proportional
        continue_button_width = int(0.12 * winWidth)  # 12% of screen width
        continue_button_height = int(0.05 * winHeight)  # 5% of screen height
        continue_button_rect = pg.Rect(winWidth // 2 - continue_button_width//2, int(0.75 * winHeight), continue_button_width, continue_button_height)
        
        # Track audio timing for delay system
        last_audio_start = 0
        audio_duration = 0
        
        while True:
            win.fill(backgroundColor)
            
            # Display instructions
            instructions = [
                "Audio Examples",
                "",
                "Click the buttons below to hear examples:",
                "Green: Sample WITH the word \"Wall\"    Blue: Actual \"Wall\"    Red: Sample WITHOUT the word \"Wall\"",
                "",
                "The blue button plays the ACTUAL \"Wall\" you should listen for",
                "",
                "When you are ready to proceed, press the continue button."
            ]
            
            y_pos = winHeight // 6
            font = pg.font.SysFont("times new roman", 28)
            
            for instruction in instructions:
                if instruction:
                    text_surface = font.render(instruction, True, BLACK)
                    text_rect = text_surface.get_rect(center=(winWidth // 2, y_pos))
                    win.blit(text_surface, text_rect)
                y_pos += 45
            
            # Check if buttons can be clicked (audio delay system)
            current_time = pg.time.get_ticks()
            time_since_last_play = current_time - last_audio_start
            can_play = (last_audio_start == 0) or (time_since_last_play >= audio_duration + 500)
            
            # Draw buttons with requested colors (dim them if not clickable)
            sample_target_color = GREEN
            actual_target_color = BLUE
            sample_distractor_color = RED
            
            pg.draw.rect(win, sample_target_color, sample_target_button_rect)      # Sample target - Green
            pg.draw.rect(win, actual_target_color, actual_target_button_rect)       # Actual target - Blue
            pg.draw.rect(win, sample_distractor_color, sample_distractor_button_rect)    # Sample distractor - Red
            pg.draw.rect(win, [255, 165, 0], continue_button_rect)  # Continue button - Orange
            
            # Add button borders
            pg.draw.rect(win, BLACK, sample_target_button_rect, 3)
            pg.draw.rect(win, BLACK, actual_target_button_rect, 3)
            pg.draw.rect(win, BLACK, sample_distractor_button_rect, 3)
            pg.draw.rect(win, BLACK, continue_button_rect, 3)
            
            # Button labels
            font = pg.font.SysFont("times new roman", 20)
            sample_target_text = font.render("Sample WITH \"Wall\"", True, WHITE)
            actual_target_text = font.render("ACTUAL \"Wall\"", True, WHITE)
            sample_distractor_text = font.render("Sample WITHOUT \"Wall\"", True, WHITE)
            continue_text = font.render("Continue", True, BLACK)
            
            win.blit(sample_target_text, sample_target_text.get_rect(center=sample_target_button_rect.center))
            win.blit(actual_target_text, actual_target_text.get_rect(center=actual_target_button_rect.center))
            win.blit(sample_distractor_text, sample_distractor_text.get_rect(center=sample_distractor_button_rect.center))
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
                    can_play = (last_audio_start == 0) or (time_since_last_play >= audio_duration + 500)
                    
                    if can_play:
                        if sample_target_button_rect.collidepoint(mouse_pos):
                            target_sound.play()
                            audio_duration = int(target_sound.get_length() * 1000)
                            last_audio_start = current_time
                        elif actual_target_button_rect.collidepoint(mouse_pos):
                            actual_target_sound.play()
                            audio_duration = int(actual_target_sound.get_length() * 1000)
                            last_audio_start = current_time
                        elif sample_distractor_button_rect.collidepoint(mouse_pos):
                            distractor_sound.play()
                            audio_duration = int(distractor_sound.get_length() * 1000)
                            last_audio_start = current_time
                    
                    if continue_button_rect.collidepoint(mouse_pos):
                        return


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

    showExamples(win, text = showExamplesText)
    pg.mouse.set_visible(False)

    win.fill(backgroundColor)
    multiLineMessage(explanationText_5, mediumFont, win)
    pg.display.flip()
    waitKey(pg.K_SPACE)

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
            question1 = 'By clicking “I agree” below, you confirm that you have read the consent form, are at least 18 years old, and agree to participate in the research. Please print or save a copy of this page for your records. By selecting “I do NOT agree” you will not be able to participate in this research and we thank you for your consideration. You may use the arrow keys to review the information in this consent form before making a decision.'
            ResponseOptions1 = ['I agree to participate in the research', 'I do NOT agree to participate in the research ']
            questions.append([question1] + ResponseOptions1)

            submitButton = Button('submit', 'tellegen', 'Submit', -1, 0) # submit button
            responses = [] # for storing answers to each question

            # iterate over each question and display to user
            for i, question in enumerate(questions):

                response = None
                running = True

                # draw the question and return how far down the screen the text goes
                yPos = multiLineMessage(question[0], mediumFont, win)

                # create all of the options for this particular questions
                buttons = [submitButton]
                for i, question_option in enumerate(question):
                    if i == 0:
                        continue
                    buttons.append(Button('option', 'tellegen', question_option, i, yPos))

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

                    # draw the question and return how far down the screen the text goes
                    multiLineMessage(question[0], mediumFont, win)

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
                    # subject's signature
                    pg.mouse.set_visible(False)
                    signature = getSubjectInfo('Signature', win)
                else:
                    consented = False
                    signature = ''
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
        writer.writerow(['Subject Number', 'Subject Name', 'Subject Email', 'Experimenter Name', 'Consented', 'Date'])
        if not consented:
            writer.writerow([subjectNumber, subjectName, subjectEmail, experimenterName, str(consented), formatted_date])
        else:
            writer.writerow([subjectNumber, signature, subjectEmail, experimenterName, str(consented), formatted_date])
    return consented

# =======================================================================
# =======================================================================

def selectStimulus(targets, distractors):

    # select a stimulus and remove it from its associated list
    masterList = targets + distractors
    stimulus = choice(masterList)
    if stimulus in targets:
        stimulusType = 'target'
        targets.remove(stimulus)
    else:
        stimulusType = 'distractor'
        distractors.remove(stimulus)

    # load the audio file
    sound = pg.mixer.Sound(stimulus)
    
    # get filename without extension for identification
    filename = os.path.basename(stimulus)
    if '.' in filename:
        filename = filename.split('.')[0]

    return sound, filename, stimulusType


# Audio playback and replay functionality
# =======================================================================

def playAudioStimulus(sound):
    """Play an audio stimulus and return the duration"""
    sound.play()
    # Get the length of the audio file in milliseconds
    duration_ms = int(sound.get_length() * 1000)
    return duration_ms

def createPlayButton():
    """Create a play button"""
    # Make button size proportional to screen
    button_width = int(0.15 * winWidth)  # 15% of screen width
    button_height = int(0.06 * winHeight)  # 6% of screen height
    button_x = (winWidth - button_width) // 2
    button_y = (winHeight - button_height) // 2 + int(0.08 * winHeight)  # Proportional offset
    
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
    
    font = pg.font.SysFont("times new roman", 24)
    text = "Play Audio"
    
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=button_rect.center)
    win.blit(text_surface, text_rect)

def drawAudioInterface(win, play_count, max_plays, audio_played=False, can_play=True, can_respond=True):
    """Draw the audio interface with instructions and play button"""
    win.fill(backgroundColor)
    
    # Instructions - update based on current state
    instructions = [
        "Click 'Play Audio' to listen to the audio sample.",
        "",
        "Then press 'Y' if you hear the target sound",
        "Press 'N' if you do not hear the target sound",
        "",
        f"Plays used: {play_count}/{max_plays}"
    ]
    
    y_pos = winHeight // 4
    font = pg.font.SysFont("times new roman", 32)
    
    for instruction in instructions:
        if instruction:  # Skip empty lines
            text_surface = font.render(instruction, True, BLACK)
            text_rect = text_surface.get_rect(center=(winWidth // 2, y_pos))
            win.blit(text_surface, text_rect)
        y_pos += 50
    
    # Draw play button
    button_rect = createPlayButton()
    enabled = play_count < max_plays and can_play
    drawPlayButton(win, button_rect, enabled, audio_played, can_play)
    
    return button_rect


def showTargetFamiliarization(win, subjectNumber, saveFolder, session_number, block_name):
    """
    Show the target familiarization screen where users can play the target sound as many times as they want.
    
    Args:
        win: pygame window
        subjectNumber: subject identifier
        saveFolder: folder to save data
        session_number: which time the user is seeing this screen (1, 2, 3, etc.)
    """
    pg.mouse.set_visible(True)
    
    # Load the actual target sound
    audio_stimuli_dir = os.path.join(os.path.dirname(__file__), 'audio_stimuli')
    
    # Use the second target file (actual target) if available, otherwise first
    actual_target_path = os.path.join(audio_stimuli_dir, 'target.wav')
    actual_target_sound = pg.mixer.Sound(actual_target_path)
    
    play_count = 0
    # Add timing variables for delay system
    last_audio_start = 0
    audio_duration = 0
    
    # Create play button (larger for this screen)
    button_width = int(0.2 * winWidth)  # 20% of screen width
    button_height = int(0.08 * winHeight)  # 8% of screen height
    play_button_rect = pg.Rect((winWidth - button_width) // 2, winHeight // 2, button_width, button_height)
    
    # Create continue button
    continue_button_width = int(0.15 * winWidth)
    continue_button_height = int(0.06 * winHeight)
    continue_button_rect = pg.Rect((winWidth - continue_button_width) // 2, int(0.75 * winHeight), continue_button_width, continue_button_height)
    
    while True:
        win.fill(backgroundColor)
        
        # Check if play button can be clicked (timing system)
        current_time = pg.time.get_ticks()
        time_since_last_play = current_time - last_audio_start
        can_play = (last_audio_start == 0) or (time_since_last_play >= audio_duration + 500)
        
        # Display instructions
        instructions = [
            "Target Sound Familiarization",
            "",
            "This is the TARGET sound you should listen for in the upcoming block.",
            "You can play it as much as you want to become familiar with it.",
            "Click 'Play Target Sound' to hear the sound again",
            "Click 'Continue' when you're ready to start the block"
        ]
        
        y_pos = winHeight // 8
        font = pg.font.SysFont("times new roman", 32)
        
        for instruction in instructions:
            if instruction:
                text_surface = font.render(instruction, True, BLACK)
                text_rect = text_surface.get_rect(center=(winWidth // 2, y_pos))
                win.blit(text_surface, text_rect)
            y_pos += 50
        
        play_button_color = BLUE
        play_text_color = WHITE
        play_text_content = "Play Target Sound"
        
        pg.draw.rect(win, play_button_color, play_button_rect)
        pg.draw.rect(win, BLACK, play_button_rect, 3)
        
        # Draw continue button (green when ready)
        continue_color = GREEN if play_count > 0 else GRAY
        pg.draw.rect(win, continue_color, continue_button_rect)
        pg.draw.rect(win, BLACK, continue_button_rect, 3)
        
        # Button labels
        font = pg.font.SysFont("times new roman", 24)
        play_text = font.render(play_text_content, True, play_text_color)
        continue_text = font.render("Continue", True, BLACK if play_count > 0 else WHITE)
        
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
                if play_button_rect.collidepoint(mouse_pos) and can_play:
                    actual_target_sound.play()
                    audio_duration = int(actual_target_sound.get_length() * 1000)
                    last_audio_start = current_time
                    play_count += 1
                elif continue_button_rect.collidepoint(mouse_pos) and play_count > 0:
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


def showPeriodicReminder(win, subjectNumber, saveFolder, trial_number, block_name):
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
    
    # Load the actual target sound
    audio_stimuli_dir = os.path.join(os.path.dirname(__file__), 'audio_stimuli')
    actual_target_path = os.path.join(audio_stimuli_dir, 'target.wav')
    actual_target_sound = pg.mixer.Sound(actual_target_path)
    
    play_count = 0
    # Add timing variables for delay system
    last_audio_start = 0
    audio_duration = 0
    
    # Create play button (larger for this screen)
    button_width = int(0.2 * winWidth)  # 20% of screen width
    button_height = int(0.08 * winHeight)  # 8% of screen height
    play_button_rect = pg.Rect((winWidth - button_width) // 2, winHeight // 2, button_width, button_height)
    
    # Create continue button
    continue_button_width = int(0.15 * winWidth)
    continue_button_height = int(0.06 * winHeight)
    continue_button_rect = pg.Rect((winWidth - continue_button_width) // 2, int(0.75 * winHeight), continue_button_width, continue_button_height)
    
    while True:
        win.fill(backgroundColor)
        
        # Check if play button can be clicked (timing system)
        current_time = pg.time.get_ticks()
        time_since_last_play = current_time - last_audio_start
        can_play = (last_audio_start == 0) or (time_since_last_play >= audio_duration + 500)
        
        # Display instructions
        instructions = [
            "Target Sound Reminder",
            "",
            f"Here's a reminder of the \"WALL\" that you are searching for.",
            f"You can play it up to {REMINDER_MAX_PLAYS} times.",
            f"Times played: {play_count}/{REMINDER_MAX_PLAYS}",
            "Click 'Play Target Sound' to hear the sound",
            "Click 'Continue' when you're ready to proceed"
        ]
        
        y_pos = winHeight // 8
        font = pg.font.SysFont("times new roman", 32)
        
        for instruction in instructions:
            if instruction:
                text_surface = font.render(instruction, True, BLACK)
                text_rect = text_surface.get_rect(center=(winWidth // 2, y_pos))
                win.blit(text_surface, text_rect)
            y_pos += 50
        
        # Draw play button with timing consideration and max plays limit
        can_click = can_play and (play_count < REMINDER_MAX_PLAYS)
        
        if can_click:
            play_button_color = BLUE
            play_text_color = WHITE
        elif play_count >= REMINDER_MAX_PLAYS:
            play_button_color = GRAY
            play_text_color = BLACK
        else:  # waiting for audio to finish
            play_button_color = [c//2 for c in BLUE]  # Dimmed blue
            play_text_color = GRAY
        
        pg.draw.rect(win, play_button_color, play_button_rect)
        pg.draw.rect(win, BLACK, play_button_rect, 3)
        
        # Draw continue button (always available)
        pg.draw.rect(win, GREEN, continue_button_rect)
        pg.draw.rect(win, BLACK, continue_button_rect, 3)
        
        # Button labels
        font = pg.font.SysFont("times new roman", 24)
        if play_count >= REMINDER_MAX_PLAYS:
            play_text_content = "Max Plays Reached"
        else:
            play_text_content = "Play Target Sound"
        
        play_text = font.render(play_text_content, True, play_text_color)
        continue_text = font.render("Continue", True, BLACK)
        
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
                if play_button_rect.collidepoint(mouse_pos) and can_click:
                    actual_target_sound.play()
                    audio_duration = int(actual_target_sound.get_length() * 1000)
                    last_audio_start = current_time
                    play_count += 1
                elif continue_button_rect.collidepoint(mouse_pos):
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


def showAudioLevelTest(win):
    """
    Show audio level testing screen for the experimenter to normalize audio levels.
    Allows playing white noise and target wall sounds as many times as needed.
    
    Args:
        win: pygame window
    """
    pg.mouse.set_visible(True)
    
    # Load audio files
    audio_stimuli_dir = os.path.join(os.path.dirname(__file__), 'audio_stimuli')
    
    # Load target wall sound
    target_path = os.path.join(audio_stimuli_dir, 'target.wav')
    target_sound = pg.mixer.Sound(target_path)
    white_noise_path = os.path.join(audio_stimuli_dir, '8khz', 'targets','6410.wav')
    white_noise_sound = pg.mixer.Sound(white_noise_path)

    
    # Track timing for delay system
    last_audio_start = 0
    audio_duration = 0
    
    # Create buttons
    button_width = int(0.2 * winWidth)  # 20% of screen width
    button_height = int(0.08 * winHeight)  # 8% of screen height
    
    # White noise button (left)
    white_noise_button_rect = pg.Rect(winWidth // 4 - button_width//2, winHeight // 2, button_width, button_height)
    
    # Target wall button (right)
    target_button_rect = pg.Rect(3 * winWidth // 4 - button_width//2, winHeight // 2, button_width, button_height)
    
    # Continue button (bottom center)
    continue_button_width = int(0.15 * winWidth)
    continue_button_height = int(0.06 * winHeight)
    continue_button_rect = pg.Rect((winWidth - continue_button_width) // 2, int(0.8 * winHeight), continue_button_width, continue_button_height)
    
    while True:
        win.fill(backgroundColor)
        
        # Check if buttons can be clicked (timing system)
        current_time = pg.time.get_ticks()
        time_since_last_play = current_time - last_audio_start
        can_play = (last_audio_start == 0) or (time_since_last_play >= audio_duration + 500)
        
        # Display instructions
        white_noise_label = "White Noise"
        
        instructions = [
            "Audio Level Testing - For Experimenter",
            "",
            "Use this screen to normalize audio levels before starting the experiment.",
            "Adjust system volume so both sounds are at comfortable levels.",
            "Recommended: Set volume so target wall is clearly audible",
            "but not uncomfortably loud.",
            "When audio levels are properly set, click 'Continue' to proceed."
        ]
        
        y_pos = winHeight // 8
        font = pg.font.SysFont("times new roman", 32)
        
        for instruction in instructions:
            if instruction:
                text_surface = font.render(instruction, True, BLACK)
                text_rect = text_surface.get_rect(center=(winWidth // 2, y_pos))
                win.blit(text_surface, text_rect)
            y_pos += 50
        
        # Draw buttons with timing consideration
        if can_play:
            white_noise_color = BLUE
            target_color = BLUE
            button_text_color = WHITE
        else:
            white_noise_color = [c//2 for c in BLUE]  # Dimmed blue
            target_color = [c//2 for c in BLUE]  # Dimmed blue
            button_text_color = GRAY
        
        # Draw white noise button
        pg.draw.rect(win, white_noise_color, white_noise_button_rect)
        pg.draw.rect(win, BLACK, white_noise_button_rect, 3)
        
        # Draw target button
        pg.draw.rect(win, target_color, target_button_rect)
        pg.draw.rect(win, BLACK, target_button_rect, 3)
        
        # Draw continue button (always green)
        pg.draw.rect(win, GREEN, continue_button_rect)
        pg.draw.rect(win, BLACK, continue_button_rect, 3)
        
        # Button labels
        font = pg.font.SysFont("times new roman", 24)
        white_noise_label = "White Noise"
        white_noise_text = font.render(white_noise_label, True, button_text_color)
        target_text = font.render("Target Wall", True, button_text_color)
        continue_text = font.render("Continue", True, BLACK)
        
        win.blit(white_noise_text, white_noise_text.get_rect(center=white_noise_button_rect.center))
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
                if can_play:
                    if white_noise_button_rect.collidepoint(mouse_pos):
                        white_noise_sound.play()
                        audio_duration = int(white_noise_sound.get_length() * 1000)
                        last_audio_start = current_time
                    elif target_button_rect.collidepoint(mouse_pos):
                        target_sound.play()
                        audio_duration = int(target_sound.get_length() * 1000)
                        last_audio_start = current_time
                
                if continue_button_rect.collidepoint(mouse_pos):
                    return

