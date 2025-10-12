import os
from math import tan, radians
from screeninfo import get_monitors

# =======================================================================
# =======================================================================

screen_width_in_centimeters = 31.5
distance_from_screen_in_centimeters = 69
number_of_sona_credits = 'xxx'

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
MAX_PLAYS = 3  # Maximum number of times a participant can play an audio stimulus

# Periodic reminder settings
REMINDER_INTERVAL = 20  # Show reminder every N trials (change this number to control frequency)
REMINDER_MAX_PLAYS = 3  # Maximum plays allowed in the reminder screen


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
In this experiment, you will listen to a series of static-y audio samples. Hidden within half of these audio samples is the word "Wall". Your goal is to decide whether the word “Wall” is present in each audio sample.' 

explanationText_2 = 'To help you think about the task, imagine you are driving toward a city while tuning your radio through static. At first, all you hear is noise, but as you get closer, faint notes or rhythms from a song begin to emerge. Even if the melody is not clear, you might sense its presence through subtle patterns in the noise.\n\n\
Similarly, in this task, you will not clearly hear the word “Wall”. Instead, you may feel as though certain patterns or impressions suggest its presence, even if it is just a hunch.\n\n\
When doing the task, many people describe the act of identifying the word as almost superstitious—a gut feeling rather than a definite perception. That is perfectly okay and expected for this task.\n\n\
The most important thing to remember is that as long as you try very hard, it is okay to rely on those superstitious feelings.'

explanationText_3 = 'To help guide you, we will allow you to hear the “Wall” that we have hidden in half the audio samples. We will also show you an example of an audio sample where the target “Wall” is present and an audio sample where the target “Wall” is absent.\n\n\
Please keep in mind that for audio samples where "Wall" is present, the word will always begin at the very start of the audio sample and end at the very end of the audio sample.\n\n\
Your job is to trust your instincts and listen for any subtle hints that suggest that the word “Wall” might be present.'

explanationText_4 = 'Here is what you need to do: \n\
        - Press "Y" if you have a sense or feeling that the word "Wall" is there, even if you are not certain.\n\
        - Press "N" if you think the word "Wall" is absent.\n\n\
Remember, even if you are unsure, as long as you are actively trying, your initial impression might still guide you to the right answer.\n\n\
Important Notes:\n\
        - If you have any questions during the task or decide to stop, please inform the experimenter immediately.\n\
        - We know how difficult this task is and really appreciate your valuable help and thank you for contributing to this study.\n\n\
When you are ready, you will listen to an example of the “Wall” that will be faintly present in half the audio samples before you begin.'

explanationText_5 = 'What to keep in mind:\n\
    - For audio samples where the word “Wall” is present, the word will always begin at the very start of the audio sample and end at the very end of the audio sample.\n\
    - Trust your instincts—this task is designed to challenge the very limits of perception.\n\
    - It is okay to feel uncertain; the goal is to make your best guess based on what you sense in the audio sample.\n\n\
Good luck, and remember that if you are actively trying, it is okay to trust your gut-feelings! \n\n\
Please try your hardest — remember, the better you do, the better your chances of winning the raffle. \n\n\
If you have any questions please ask the experimenter now.\n\n\
You will be asked to respond to a single question and then you will be presented with the target "Wall". You will be allowed to replay it as many times as you like before you begin, and you will be allowed to listen to it again at various points throughout the experiment.\n\n\
The main portion of experiment will begin immediately after you listen to the target "Wall".'

showExamplesText = 'On the left is an example of an image where the “H” is present, while on the right is an image where the “H” is absent. As you can see, this task is quite difficult. Just from looking at the differences between these images, you can tell that identifying the “H” will not come from clearly seeing it. Instead, you may find yourself relying on subtle impressions, patterns, or even a gut feeling that the “H” is there.\n\n\
    Press the spacebar to continue.'
# 'Welcome to this fascinating visual perception task! As part of this experiment, you will encounter a series of images filled with a mix of black and white dots. Within half of these images, a black "H" will be subtly embedded. Your challenge is to identify whether the "H" is present in each image. This task will test the limits of your perception, urging you to trust the subtle hints and the instincts that might suggest the presence of the "H".\n\n\
# Even though spotting the "H" might seem daunting at first, believe in your intuitive abilities. Research has consistently shown that people can perform remarkably well on such tasks, often exceeding their own expectations. The "H" will be centered but obscured, and we will provide you with a reference image of the "H" before you start, to help guide your observations.\n\n\
# When you are ready to make a decision for each image, press "Y" if you feel the "H" is there, or press "N" if you think it is absent. Remember, more often than not, your first impression might be more accurate than you realize.\n\n\
# We thank you for participating and value your contributions to this study. Should you have any questions, or if you decide to stop participating, please inform your experimenter immediately.\n\n\
# Press the spacebar when you are ready to begin the experiment. Good luck, and trust in the power of your perception!'


realText = 'Remember, you are listening for the word "Wall". The word will always begin at the very start of the audio sample and end at the very end of the audio sample. It is present in half of the audio samples.\n\n\
You will be given the opportunity to listen to the actual "Wall" that is hidden in the audio samples before beginning the next block. After that, you will begin listening to audio samples again. Press "Y" if you believe the "Wall" is in the audio sample, and press "N" if you do not believe that you hear it. The task consists of two blocks, and you will receive a short break between each block to rest.\n\n\
Press the spacebar when you are ready to proceed and start making your selections.\n\n\
Good luck, and believe in yourself! It is normal to feel unsure, as many participants think they are not doing well, but you will likely perform better than you expect!'

realTextAlt = 'Remember, you are listening for the word "Wall". The word will always begin at the very start of the audio sample and end at the very end of the audio sample. It is present in half of the audio samples.\n\n\
You will be given the opportunity to listen to the actual "Wall" that is hidden in the audio samples before beginning the next block. After that, you will listen to audio samples again. Press "Y" if you believe the "Wall" is in the audio sample, and press "N" if you do not believe the "Wall" is in the audio sample.\n\n\
Good luck, and believe in yourself! It is normal to feel unsure, as many participants think they are not doing well, but you will likely perform better than you expect! Please try your hardest — remember, the better you do, the better your chances of winning the raffle.\n\n\
You will be asked to respond to a single question and then you will be presented with the target "Wall". You will be allowed to replay it as many times as you like before you begin, and you will be allowed to listen to it again at various points throughout the experiment.\n\n\
The main portion of experiment will resume immediately after you listen to the target "Wall".'

def breakScreenText(i):
    return f'You have now completed {i} out of 2 blocks.\n\n You have earned a break.\n\n Please let the experimenter know.\n\n\
When you are ready you will listen to the target "Wall" again and resume your task.\n\n'

exitScreenText = 'Thank you for participating in this study!\n\n'\
'Please notify the experimenter that you have completed the study.\n\n'\

questionnairesIntroText = 'You will now respond to some questionnaires.\n\nPlease read each question carefully and respond truthfully.\n\nPress the spacebar to begin.'
telleganScaleText = 'Please respond True or False to the following questions.\n\nPress the spacebar to begin.'
launeyScaleText = 'Please indicate the degree to which the following statements describe you on a scale from 1 (not at all like me) to 8 (extremely like me).\n\nPress the spacebar to begin.'
dissociativeExperiencesText = 'This questionnaire consists of twenty-eight questions about experiences that you may have in your daily life. We are interested in how often you have these experiences. It is important, however, that your answers show how often these experiences happen to you when you are not under the influence of alcohol or drugs.\n\nTo answer the questions, please determine to what degree the experience described in the question applies to you and click the box corresponding to what percentage of the time you have the experience.\n\n Press the spacebar to begin.'

flow_state_instructions = 'Please respond to this questionnaire about your experience so far. \n\nPress the spacebar to continue.'
studyInfoText = f'Study Number: IRB24-1770\nStudy Title: Superstitious Perception\nResearcher(s): Shannon Heald\n\n\
Description: We are researchers at the University of Chicago doing a research study about the limits of human perception. You will be asked to engage with different types of stimuli (such as images and sounds) and indicate whether or not you believe a particular target is present within them. You will also be asked to fill out a couple of questionnaires.\n\n\
Participation should take approximately 90 minutes.\nYour participation is voluntary.\n\n\
Incentives: You will be compensated {number_of_sona_credits} SONA Credits for your participation in this study. You will also be entered into a raffle for a 50 dollar Amazon gift card. Your performance on the study will influence your chances of winning the raffle. The better you do, the higher your chances are to win the giftcard.\n\n\
Please press the right arrow key to continue.'

risksAndBenefitsText = 'Risks and Benefits: Your participation in this study does not involve any risk to you beyond that of everyday life. \n\nRisks for this task are minimal and include boredom, minor fatigue, and the possibility of a breach of confidentiality. \n\nTaking part in this research study may not benefit you personally beyond learning about psychological research, but we may learn new things that could help others and contribute to the field of psychology.\n\nPress the right arrow key to continue and the left arrow key to go back.'

confidentialityText = 'Confidentiality: Any identifiable data or information collected by this study will never be shared outside the research team. \n\nDe-identified information from this study may be used for future research studies or shared with other researchers for future research without your additional informed consent. \n\nWe may also upload your data (in both aggregate and individual form) to public data repositories. \n\nYour study data will be handled as confidentially as possible. If results of this study are published or presented, your individual name will not be used. \n\nIf you decide to withdraw from this study, any data already collected will be destroyed.\n\nPress the right arrow key to continue and the left arrow key to go back.'

contactsAndQuestionsText = 'Contacts & Questions: If you have questions or concerns about the study, you can contact Jean Matelski Boulware at (312)860-9260 or at matelskiboulware@uchicago.edu.\n\nIf you have any questions about your rights as a participant in this research, feel you have been harmed, or wish to discuss other study-related concerns with someone who is not part of the research team, you can contact the University of Chicago Social & Behavioral Sciences Institutional Review Board (IRB) Office by phone at (773) 702-2915, or by email at sbs-irb@uchicago.edu.\n\nPress the right arrow key to continue and the left arrow key to go back.'

nonConsentText = 'Thank you for considering our experiment. \n\nPlease press the spacebar to exit the experiment.'
# =======================================================================
# =======================================================================            
    

 