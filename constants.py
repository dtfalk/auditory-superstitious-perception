import os
from math import tan, radians
from screeninfo import get_monitors

# =======================================================================
# =======================================================================

screen_width_in_centimeters = 31.5
distance_from_screen_in_centimeters = 69
number_of_sona_credits = '1.5'

# get screen size for each monitor in the syste m
winfo = get_monitors()
if len(winfo) > 1:
    winX = winfo[1].x
    winY = winfo[1].y
    winWidth = winfo[1].width
    winHeight = winfo[1].height

else:
    winX = winfo[0].x
    winY = winfo[0].y
    winWidth = winfo[0].width
    winHeight = winfo[0].height


os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (winX, winY)

# Get the size in pixels for 2 degrees of visual angle
def deg2pix():
    
    
    # Calculate the total visual angle width in cm
    width_in_cm = 2 * distance_from_screen_in_centimeters * tan(radians(1))
    
    # Calculate the number of pixels per degree as
    pixels_per_cm = winWidth / screen_width_in_centimeters

    # total pixel width
    total_width_in_pixels = width_in_cm * pixels_per_cm

    return total_width_in_pixels

# gives us the size we must scale the images by
stimSize = round(deg2pix())

# screen center for drawing images
screenCenter = ((winWidth // 2) - (stimSize // 2), (winHeight // 2) - (stimSize // 2))

# Audio experiment settings
MAX_PLAYS = 1  # Maximum number of times a participant can play an audio stimulus

# Periodic reminder settings
REMINDER_INTERVAL = 2 # Show reminder every N trials (change this number to control frequency)
REMINDER_MAX_PLAYS = 3  # Maximum plays allowed in the reminder screen
FAMILIARIZATION_MAX_PLAYS = 3 # Maximum plays during the refresher screen


# define some font sizes and colors for easy access

# == Font sizes ==
extraLargeFont = winHeight // 5
largeFont = winHeight // 10
mediumFont = winHeight // 20
smallFont = winHeight // 30

# == Greyscale ==
BLACK = [0, 0, 0]
WHITE = [255, 255, 255]
BLUE = [50, 50, 255]
GRAY = [128, 128, 128]
GREY = [128, 128, 128]
SLATEGREY = [112, 128, 144]
DARKSLATEGREY = [47, 79, 79]


# == Yellows ==
YELLOW = [255, 255, 0]
OLIVE = [128,128,0]
DARKKHAKI = [189,183,107]

# == Greens ==
GREEN = [0, 128, 0]
GREENYELLOW = [173, 255, 47]

RED = [255, 50, 50]


backgroundColor = GREY # background color for screen
textColor = BLACK # text color

# =======================================================================
# =======================================================================

# This block of code defines the valid characters and numbers for text entry
# =======================================================================
# =======================================================================

# getting the valid letters and numbers for user info.
def getValidChars():
    validLetters = []
    validNumbers = []
    
    # valid digits (0 - 9)
    for i in range(48, 58):
        validNumbers.append(chr(i))
        
    # valid lowercase letters (a - z)
    for i in range(97, 123):
        validLetters.append(chr(i))
        
    # valid uppercase letters (A - Z)
    for i in range(65, 91):
        validLetters.append(chr(i))
    
    return validLetters, validNumbers

validLetters, validNumbers = getValidChars()

# =======================================================================
# =======================================================================


# This block of code contains the text for explanation screens
# =======================================================================
# =======================================================================

explanationText_1 = 'Welcome to the experiment!\n\n\
In this experiment, you will listen to a series of short, static-like audio samples. For each sample, your task is to decide whether a specific word is present in the sound.\n\n\
The word you will be listening for is \"Wall\".\n\n\
This task is intentionally very difficult. The audio samples will mostly sound like noise, and the word will never be clearly spoken or easy to hear. Many people report feeling unsure whether they ever truly hear the word they are searching for.\n\n\
Even so, people typically perform well on this task despite feeling uncertain. Feeling unsure or unconfident is normal and expected.\n\n\
Your job is not to clearly identify the word, but to listen carefully and decide whether the sound gives you the impression that the word \"Wall\" might be present.'

explanationText_2 = 'To help you think about this task, imagine overhearing someone speaking through a wall or a closed door. You can tell that a voice might be there, but the sound is muffled and buried in ambient noise. You strain to listen, trying to pick out speech, and sometimes it feels like a specific word or phrase might have been present, even though you are never sure.\n\n\
This task is similar in spirit, but the word that you are listening for will be even more difficult to discern. You will never clearly hear the word \"Wall\". Instead, you may find yourself caught between hearing and guessing, where the sound creates a vague impression rather than a definite perception.\n\n\
Many people describe this experience as a strange or superstitious feeling, where intuition, along with faint internal impressions or sensations, guides decisions more than clear evidence.\n\n\
That uneasy, in-between feeling is not a mistake or a sign that something is wrong. These subtle thoughts and impressions are a meaningful part of yourself that is quietly trying to make itself known.\n\n\
Your job is to engage with these thoughts and feelings, take them seriously, and listen carefully to what they are trying to tell you.'

explanationText_3 = 'As mentioned earlier, throughout this experiment you will always be listening for the word \"Wall\".\n\n\
Importantly, you will always be listening for the word \"Wall\" as it occurs within the context of this sentence:\n\n\
\"The picture hung on the wall.\"\n\n\
Rather than searching for an isolated word, this sentence provides the context that shapes how the word \"Wall\" would naturally sound.\n\n\
You will be introduced to a specific speaker, and you will hear a recording of the speaker saying the full sentence aloud.\n\n\
During the task, you are always searching for this speaker’s version of the word \"Wall\", as it would naturally occur at the end of this sentence.\n\n\
The audio samples you will listen to during the task will not clearly sound like the speaker’s voice. Instead, they will sound like noise. In some of these samples, traces of the speaker’s word \"Wall\" have been hidden within the noise.\n\n\
Your task is to decide whether the speaker’s \"Wall\", as spoken in the context of the sentence, seems to be present in each audio sample.'

explanationText_4 = 'What to keep in mind:\n\
    - When the word \"Wall\" is present, it always spans the entire audio sample from beginning to end.\n\
    - You should base your response on whatever impression or feeling the sound gives you, even if you are not confident.\n\n\
Important notes:\n\
    - If you have any questions at any point or wish to stop, please tell the experimenter immediately.\n\
    - We know this task is challenging and truly appreciate your effort and participation.\n\
    - Please try your best. Better performance increases your chances of winning the raffle.\n\
    - If you are actively trying, it is okay to trust your intuition.\n\n\
If you have any questions, please ask the experimenter now.'

explanationText_5 = 'A final note before beginning:\n\n\
Even with the sentence context and the speaker in mind, the audio samples you will hear will remain extremely noisy. You will never clearly hear the word \"Wall\" spoken in the samples.\n\n\
It is normal for many trials to feel uncertain, ambiguous, or as though nothing definite is there at all.\n\n\
That experience is expected. Doing well on this task does not require certainty or confidence, but a willingness to stay engaged and respond based on the impressions you have, even when they feel faint or unclear.'


# Block-specific instruction text
# NOTE: If you want a specific sentence participants should imagine, edit IMAGINED_SENTENCE_TO_IMAGINE.
IMAGINED_SENTENCE_TO_IMAGINE = 'The Picture Hung On The Wall'

fullSentenceBlockInstructionsText = (
    "In this part of the experiment, on each trial you will hear a recording of the speaker saying this sentence before you make your judgement:\n\n"
    "\"The picture hung on the wall.\"\n\n"
    "The sentence is always the same, except that the final word is replaced by a short, static-like audio sample.\n\n"
    "Your task on each trial is to decide whether the speaker’s \"Wall\", as it would naturally complete the sentence, seems to be present in that noisy audio sample.\n\n"
    "A few important points:\n"
    "   - The audio samples themselves are not clearly spoken words. They are noisy clips that may or may not contain traces of the speaker’s \"Wall\".\n"
    "   - If the speaker’s \"Wall\" is present, it spans the entire audio sample from beginning to end.\n"
    "   - You are always judging whether the speaker’s version of \"Wall\" is present in the audio sample, NOT your own imagined version.\n\n"
    "Next, you will listen to the speaker say the full sentence as many times as you like.\n\n"
    "Press the spacebar to continue."
)


imaginedSentenceBlockInstructionsText = (
    "In this part of the experiment, you will imagine the speaker saying this sentence before you make your judgment:\n\n"
    "\"The picture hung on the wall.\"\n\n"
    "On each trial, you will imagine the speaker saying the beginning of this sentence in their voice.\n\n"
    "As your imagined sentence reaches the word \"Wall\", you will click \"Play Audio\" to hear a short, static-like audio sample.\n\n"
    "Your task is to decide whether the speaker’s \"Wall\", as it would naturally complete the sentence, seems to be present in that noisy audio sample.\n\n"
    "A few important points:\n"
    "   - The audio samples themselves are not clearly spoken words. They are noisy clips that may or may not contain traces of the speaker’s \"Wall\".\n"
    "   - If the speaker’s \"Wall\" is present, it spans the entire audio sample from beginning to end.\n"
    "   - You are always judging whether the speaker’s version of \"Wall\" is present in the audio sample, NOT your own imagined version.\n"
    "   - You may only IMAGINE the sentence. Do not say the sentence out loud, move your lips or otherwise subvocalize. \n\n"
    "Next, you will hear the speaker say the full sentence as many times as you like.\n\n"
    "Press the spacebar to continue."
)





# Trial-by-trial instruction text (shown on every trial screen)
# Edit these lists if you want different wording per block.
trialInstructions_full_sentence = [
    "Click 'Play Audio' to listen to the speaker saying the sentence.",
    "",
    "After listening, respond as quickly as you feel comfortable.",
    "Press 'Y' if you believe the speaker's \"Wall\" is hidden in the noisy audio sample.",
    "Press 'N' if you believe the speaker's \"Wall\" is NOT hidden in the noisy audio sample.",
]

trialInstructions_imagined_sentence = [
    "Silently imagine the speaker saying this sentence in their voice:",
    f'{IMAGINED_SENTENCE_TO_IMAGINE}',
    "Imagine the speaker saying the beginning of the sentence and click 'Play Audio' when your imagined sentence reaches the word \"Wall\".",
    "After listening, respond as quickly as you feel comfortable.",
    "Press 'Y' if you believe the speaker's \"Wall\" is hidden in the noisy audio sample.",
    "Press 'N' if you believe the speaker's \"Wall\" is NOT hidden in the noisy audio sample.",
]


# Screen shown immediately before the first trial of each block
preTrialQuickResponseTextFullSentence = (
    "Before you begin:\n\n"
    "- On each trial, you will hear the sentence once, with the final word replaced by a noisy audio sample.\n"
    "- Each audio sample can only be heard one time. There are no replays.\n"
    "- When you are ready to respond, press \"Y\" if you sense that the speaker’s \"Wall\" is present, and \"N\" if you believe it is not.\n"
    "- Please respond quickly after hearing the stimulus.\n\n"
    "On the next screen, you will be asked to respond to a single question.\n"
    "After that, you will hear the sentence again to prepare, and the real trials will begin immediately.\n\n"
    "Trust your gut feelings. It is okay to be uncertain.\n\n"
    "Press the spacebar to continue."
)


preTrialQuickResponseTextImaginedSentence = (
    "Before you begin:\n\n"
    "- On each trial, you will imagine the speaker saying the sentence, then listen to a noisy audio sample.\n"
    "- Each audio sample can only be heard one time. There are no replays.\n"
    "- When you are ready to respond, press \"Y\" if you believe the speaker’s \"Wall\" is present, and \"N\" if you believe it is not.\n"
    "- Please respond quickly after hearing the stimulus.\n\n"
    "- On every trial, imagine the sentence in the speaker’s voice and click \"Play Audio\" at the moment you would be imagining the word \"Wall\".\n"
    "- The sentence must be imagined silently. Do not say it out loud, under your breath, or move your mouth.\n\n"
    "On the next screen, you will be asked to respond to a single question.\n"
    "After that, you will hear the sentence again to prepare, and the real trials will begin immediately.\n\n"
    "Trust your gut feelings. It is okay to be uncertain.\n\n"
    "Press the spacebar to continue."
)


def breakScreenText(i):
    return f'You have now completed {i} out of 2 blocks.\n\n You have earned a break.\n\n Please let the experimenter know.\n\n\
When you are ready you will listen to the target “Wall” again and resume your task.\n\n'

exitScreenText = 'Thank you for participating in this study!\n\n'\
'Please notify the experimenter that you have completed the study.\n\n'\

questionnairesIntroText = 'You will now respond to some questionnaires.\n\nPlease read each question carefully and respond truthfully.\n\nPress the spacebar to begin.'
telleganScaleText = 'Please respond True or False to the following questions.\n\nPress the spacebar to begin.'
launeyScaleText = 'Please indicate the degree to which the following statements describe you on a scale from 1 (not at all like me) to 8 (extremely like me).\n\nPress the spacebar to begin.'
dissociativeExperiencesText = 'This questionnaire consists of twenty-eight questions about experiences that you may have in your daily life. We are interested in how often you have these experiences. It is important, however, that your answers show how often these experiences happen to you when you are not under the influence of alcohol or drugs.\n\nTo answer the questions, please determine to what degree the type of experience described in the question applies to you and click the box corresponding to what percentage of the time you have the experience.\n\n Press the spacebar to begin.'

flow_state_instructions = 'Please respond to this questionnaire about your experience so far. \n\nPress the spacebar to begin.'
studyInfoText = f'Study Number: IRB24-1770\nStudy Title: Superstitious Perception\nResearcher(s): Shannon Heald\n\n\
Description: We are researchers at the University of Chicago doing a research study about the limits of human perception. You will be asked to engage with different types of stimuli (such as images and sounds) and indicate whether or not you believe a particular target is present within them. You will also be asked to fill out a couple of questionnaires.\n\n\
Depending on your performance, we may reach out to you for follow up studies. If we reach out to you again, your participation is entirely voluntary, and you will be compensated for any further experiments in which you are a participant.\n\n\
Participation should take approximately 45-90 minutes.\nYour participation is voluntary.\n\n\
Incentives: You will be compensated {number_of_sona_credits} SONA Credits for your participation in this study. You will also be entered into a raffle for a 50 dollar Amazon gift card. Your performance on the study will influence your chances of winning the raffle. The better you do, the higher your chances are to win the giftcard.\n\n\
Please press the right arrow key to continue.'

risksAndBenefitsText = 'Risks and Benefits: Your participation in this study does not involve any risk to you beyond that of everyday life. \n\nRisks for this task are minimal and include boredom, minor fatigue, and the possibility of a breach of confidentiality. \n\nTaking part in this research study may not benefit you personally beyond learning about psychological research, but we may learn new things that could help others and contribute to the field of psychology.\n\nPress the right arrow key to continue and the left arrow key to go back.'

confidentialityText = 'Confidentiality: Any identifiable data or information collected by this study will never be shared outside the research team. \n\nDe-identified information from this study may be used for future research studies or shared with other researchers for future research without your additional informed consent. \n\nWe may also upload your data (in both aggregate and individual form) to public data repositories. \n\nYour study data will be handled as confidentially as possible. If results of this study are published or presented, your individual name will not be used. \n\nIf you decide to withdraw from this study, any data already collected will be destroyed.\n\nPress the right arrow key to continue and the left arrow key to go back.'

contactsAndQuestionsText = 'Contacts & Questions: If you have questions or concerns about the study, you can contact Jean Matelski Boulware at (312)860-9260 or at matelskiboulware@uchicago.edu.\n\nIf you have any questions about your rights as a participant in this research, feel you have been harmed, or wish to discuss other study-related concerns with someone who is not part of the research team, you can contact the University of Chicago Social & Behavioral Sciences Institutional Review Board (IRB) Office by phone at (773) 702-2915, or by email at sbs-irb@uchicago.edu.\n\nPress the right arrow key to continue and the left arrow key to go back.'

nonConsentText = 'Thank you for considering our experiment. \n\nPlease press the spacebar to exit the experiment.'
# =======================================================================
# =======================================================================            
    

 