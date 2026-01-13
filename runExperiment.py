import pygame as pg
from random import shuffle
from time import sleep
from helperFunctions import *
from questionnaires import main as questions
from questionnaires import flow_state_scale, stanford_sleepiness_scale


def showTargetFamiliarizationWrapper(win, subjectNumber, saveFolder, familiarization_session_count, block_name):
    """
    Wrapper function to show target familiarization and increment session count.
    Returns the updated session count.
    """
    familiarization_session_count += 1
    showTargetFamiliarization(win, subjectNumber, saveFolder, session_number=familiarization_session_count, block_name=block_name)
    return familiarization_session_count


# The experiment itself
def experiment(subjectNumber, block, targets, distractors, saveFolder, win):

    # various variables for handling the game
    pg.event.clear()
    reset = False
    startTime = pg.time.get_ticks()
    play_count = 0  # Changed from replay_count to play_count
    audio_played = False  # Track if audio has been played at least once
    last_audio_start = 0  # Track when audio last started playing
    audio_duration = 0  # Track how long the audio lasts
    
    # Track trial number within this block (starting from 0 for each block)
    trial_number = 0
    
    # select an initial audio stimulus
    if block == 'full_sentence':
        prefix_wav = os.path.join(os.path.dirname(__file__), "audio_stimuli", "fullsentenceminuswall.wav")
    else:
        prefix_wav = None
    sound, stimulusNumber, stimulusType = selectStimulus(targets, distractors, prefix_wav)
    
    # Don't auto-play the initial audio stimulus - let user press button

    # Loop for handling events
    while True:
        
        # Draw the audio interface
        if not reset:
            current_time = pg.time.get_ticks()
            time_since_last_play = current_time - last_audio_start
        
            can_play = (last_audio_start == 0) or (time_since_last_play >= audio_duration + 500)
            can_respond = audio_played and (last_audio_start > 0) and (time_since_last_play >= audio_duration + 500)
            button_rect = drawAudioInterface(win, play_count, MAX_PLAYS, audio_played, can_play, can_respond, block_name=block)
            pg.display.flip()
        
        # handles key presses and mouse clicks
        for event in pg.event.get():
            if event.type == pg.KEYDOWN and not reset:

                # quit the experiment key
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()

                # handles response keys (y for "yes, the stimulus is here". "n" otherwise)
                # Now requires that audio has been played AND enough time has passed for it to finish
                elif (event.key == pg.K_y or event.key == pg.K_n) and audio_played:
                    current_time = pg.time.get_ticks()
                    time_since_last_play = current_time - last_audio_start
                    audio_finished = (last_audio_start > 0) and (time_since_last_play >= audio_duration + 500)
                    
                    if audio_finished:
                        # indicates we will reset the experiment once a response is selected
                        reset = True

                        # user's response to a stimulus
                        if event.key == pg.K_y:
                            response = 'target'
                        else:
                            response = 'distractor'

                        # saves user's response (including play count)
                        responseTime = pg.time.get_ticks() - startTime
                        recordResponse(subjectNumber, block, stimulusNumber, stimulusType, response, responseTime, saveFolder, play_count)
                        
                        # 2 second rest between each stimulus
                        win.fill(backgroundColor)
                        pg.display.flip()
                        sleep(2)
                        pg.event.clear()
            
            # Handle mouse clicks for play button
            elif event.type == pg.MOUSEBUTTONDOWN and not reset:
                mouse_pos = pg.mouse.get_pos()
                current_time = pg.time.get_ticks()
                # Check if enough time has passed since last audio play (audio duration + 500ms)
                time_since_last_play = current_time - last_audio_start
                can_play = (last_audio_start == 0) or (time_since_last_play >= audio_duration + 500)
                
                if button_rect.collidepoint(mouse_pos) and play_count < MAX_PLAYS and can_play:
                    audio_duration = playAudioStimulus(sound)
                    last_audio_start = current_time
                    play_count += 1
                    audio_played = True
                    # Reset timer when audio is first played
                    if play_count == 1:
                        startTime = pg.time.get_ticks()
        # end of a trial
        if reset:
            # Increment trial number
            trial_number += 1
            
            # Check if we should show periodic reminder (but not after the last trial)
            remaining_stimuli = len(targets) + len(distractors)
            if (trial_number % REMINDER_INTERVAL == 0) and (remaining_stimuli > 0):
                showPeriodicReminder(win, subjectNumber, saveFolder, trial_number, block)

            # update the restart variables 
            reset = False
            play_count = 0  # Reset play count for new stimulus
            audio_played = False  # Reset audio played flag
            last_audio_start = 0  # Reset audio timing
            audio_duration = 0  # Reset audio duration
            
            # end experiment if we have shown all of the audio stimuli
            if remaining_stimuli == 0:
                return  # Return without trial count since it resets per block
            
            # otherwise select a new audio stimulus
            sound, stimulusNumber, stimulusType = selectStimulus(targets, distractors, prefix_wav)

            # clear events so spamming keys doesn't mess things up
            pg.event.clear()


# handles the overall experiment flow
def main():

    # Initializing Pygame
    # =================================================================

    # == Initiate pygame and collect user information ==
    pg.init()
    pg.mixer.init()

    # == Set window ==
    win = pg.display.set_mode((winWidth, winHeight), pg.FULLSCREEN)
    pg.mouse.set_visible(False)

    # =================================================================


    
    # Collects user info and preps the stimuli and the rest of the experiment
    # ============================================================================================

    # Audio level testing for experimenter
    showAudioLevelTest(win)

    # get user info and where to store their results
    experimenterName = getSubjectInfo('experimenter name', win)
    subjectNumber = getSubjectInfo('subject number', win)
    subjectName = getSubjectInfo('subject name', win)
    subjectEmail = getSubjectInfo('subject email', win)

    # create a new folder for the subject's results
    saveFolder = os.path.join(os.path.dirname(__file__), 'results', subjectNumber)
    while os.path.exists(saveFolder):
        subjectNumber = subjectNumber + '0'
        saveFolder = os.path.join(os.path.dirname(__file__), 'results', subjectNumber)
    os.makedirs(saveFolder, exist_ok = True)

    # Track target familiarization sessions
    familiarization_session_count = 0

    # Collects the stimuli for each condition and shuffles them
    full_sentence_targets, full_sentence_distractors, imagined_sentence_targets, imagined_sentence_distractors = getStimuli()
    block_dictionary = {
        'full_sentence': (full_sentence_targets, full_sentence_distractors),
        'imagined_sentence': (imagined_sentence_targets, imagined_sentence_distractors)
    }
    block_names = list(block_dictionary.keys())
    shuffle(block_names)
    blocks = [block_dictionary[name] for name in block_names]

    # ============================================================================================
    
    # Get the user's consent and explain the experiment
    consented = consentScreen(subjectName, subjectNumber, subjectEmail, experimenterName, win)
    if not consented:
        nonConsentScreen(win)
    sleepiness_responses = []
    experimentExplanation(win)
    pg.event.clear()

    # give users all blocks
    for i, (block_name, (targets, distractors)) in enumerate(zip(block_names, blocks)):

        # Block-specific instructions + examples
        showBlockInstructions(win, block_name)
        stanford_sleepiness_scale(sleepiness_responses, win)

        # Show target familiarization before each block
        familiarization_session_count = showTargetFamiliarizationWrapper(win, subjectNumber, saveFolder, familiarization_session_count, block_name)

        # display stimuli
        pg.mouse.set_visible(True)
        experiment(
            subjectNumber = subjectNumber, 
            block = block_name, 
            targets = targets, 
            distractors = distractors, 
            saveFolder = saveFolder, 
            win = win)   
        
        # After first block (round one), add Stanford Sleepiness Scale labeled as "before break"
        if i == 0:  # After first block
            subjectExplanation_methodology = getSubjectInfo('selfReflect_explanation', win)
            with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'selfReflect_methodology_{block_name}_{subjectNumber}.txt'), mode = 'w') as f:
                f.write(subjectExplanation_methodology)

            subjectExplanation_changes = getSubjectInfo('selfReflect_changes', win)
            with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'selfReflect_changes_{block_name}_{subjectNumber}.txt'), mode = 'w') as f:
                f.write(subjectExplanation_changes)
            stanford_sleepiness_scale(sleepiness_responses, win, label="before break")
            pg.mouse.set_visible(False)
        
        # give break screen between blocks
        if i < len(blocks) - 1:
            breakScreen(i + 1, win)
        
        if i == len(block_names) - 1:
            subjectExplanation_methodology = getSubjectInfo('selfReflect_explanation', win)
            with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'selfReflect_methodology_{block_name}_{subjectNumber}.txt'), mode = 'w') as f:
                f.write(subjectExplanation_methodology)

            subjectExplanation_changes = getSubjectInfo('selfReflect_changes', win)
            with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'selfReflect_changes_{block_name}_{subjectNumber}.txt'), mode = 'w') as f:
                f.write(subjectExplanation_changes)
            stanford_sleepiness_scale(sleepiness_responses, win)
        
    # display questionnaires
    questions(subjectNumber, win)

    # write the responses to a csv file with the questionnaire's name
    with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'stanford_sleepiness_{subjectNumber}.csv'), mode = 'w', newline = '') as f:
        writer = csv.writer(f)
        header = ['Subject Number', 'Pre-Experiment', 'Pre-Break Post-Block-1','Post-Break Pre-Block-2', 'Post-Experiment']
        writer.writerow(header)
        writer.writerow([subjectNumber] + [''.join([ch for ch in response if ch.isdigit()]) for response in sleepiness_responses])

    # exit screen thanking participants
    exitScreen(subjectNumber, win)

    # calculate overall data and write to a user-specific data file
    writeSummaryData(subjectNumber, block_names, saveFolder)

if __name__ == '__main__':
    main()