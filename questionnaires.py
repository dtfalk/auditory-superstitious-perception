from constants import *
import pygame as pg
from constants import *
import sys
import os
from helperFunctions import multiLineMessage, waitKey
import csv

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
            if questionnaireName == 'tellegen':
                scalar = 1.75
            elif questionnaireName == 'launay':
                scalar = 1.4
            elif questionnaireName == 'dissociative':
                scalar = 1.5
            elif questionnaireName == 'sleepiness':
                scalar = 1.3
                self.fontSize = int(0.85 * base_medium_font)
            elif questionnaireName == 'vhq':
                scalar = 1.4  # Similar spacing to launay
            elif "bias" in questionnaireName:
                scalar = 1.3
            else:
                scalar = 1.5  # Default fallback for any unknown questionnaire types
            spacing = scalar * i * self.fontSize 
            buffer = current_h // 20
            maxY = (0.85 * current_h) - self.fontSize
            
            # Make option button size proportional to screen
            button_size = int(0.015 * min(current_w, current_h))  # 1.5% of smaller screen dimension
            button_size = max(button_size, self.fontSize)  # Ensure it's at least as big as font
            
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

# contains questionnaire questions and displays questionnaire to the subject
def tellegen(subjectNumber, win):

    # variables to hold all of the questions and their associated response options
    questions = []

    # question 1 text and response options
    question1 = 'Sometimes I feel and experience things as I did when I was a child.'
    ResponseOptions1 = ['True', 'False']
    questions.append([question1] + ResponseOptions1)

    question2 = 'I can be greatly moved by eloquent or poetic language.'
    ResponseOptions2 = ['True', 'False']
    questions.append([question2] + ResponseOptions2)

    question3 = 'While watching a movie, a T.V. show, or a play, I may become so involved that I forget about myself and my surroundings and experience the story as if I were taking part in it.'
    ResponseOptions3 = ['True', 'False']
    questions.append([question3] + ResponseOptions3)

    question4 = 'If I stare at a picture and then look away from it, I can sometimes “see” an image of the picture, almost as if I were looking at it.'
    ResponseOptions4 = ['True', 'False']
    questions.append([question4] + ResponseOptions4)

    question5 = 'Sometimes I feel as if my mind could envelop the whole world.'
    ResponseOptions5 = ['True', 'False']
    questions.append([question5] + ResponseOptions5)

    question6 = 'I like to watch cloud shapes change in the sky.'
    ResponseOptions6 = ['True', 'False']
    questions.append([question6] + ResponseOptions6)

    question7 = 'If I wish, I can imagine (or daydream) some things so vividly that they hold my attention as a good movie or story does.'
    ResponseOptions7 = ['True', 'False']
    questions.append([question7] + ResponseOptions7)

    question8 = 'I think I really know what some people mean when they talk about mystical experiences.'
    ResponseOptions8 = ['True', 'False']
    questions.append([question8] + ResponseOptions8)

    question9 = 'I sometimes “step outside” my usual self and experience an entirely different state of being.'
    ResponseOptions9 = ['True', 'False']
    questions.append([question9] + ResponseOptions9)
    
    question10 = 'Textures - such as wool, sand, wood - sometimes remind me of colors or music.'
    ResponseOptions10 = ['True', 'False']
    questions.append([question10] + ResponseOptions10)

    question11 = 'Sometimes I experience things as if they were doubly real.'
    ResponseOptions11 = ['True', 'False']
    questions.append([question11] + ResponseOptions11)

    question12 = "When I listen to music, I can get so caught up in it that I don't notice anything else."
    ResponseOptions12 = ['True', 'False']
    questions.append([question12] + ResponseOptions12)

    question13 = 'If I wish, I can imagine that my body is so heavy that I could not move it if I wanted to.'
    ResponseOptions13 = ['True', 'False']
    questions.append([question13] + ResponseOptions13)

    question14 = 'I can often somehow sense the presence of another person before I actually see or hear her/him/them.'
    ResponseOptions14 = ['True', 'False']
    questions.append([question14] + ResponseOptions14)

    question15 = 'The crackle and flames of a wood fire stimulate my imagination.'
    ResponseOptions15 = ['True', 'False']
    questions.append([question15] + ResponseOptions15)

    question16 = 'It is sometimes possible for me to be completely immersed in nature or in art and to feel as if my whole state of consciousness has somehow been temporarily altered.'
    ResponseOptions16 = ['True', 'False']
    questions.append([question16] + ResponseOptions16)

    question17 = 'Different colors have distinctive and special meaning to me.'
    ResponseOptions17 = ['True', 'False']
    questions.append([question17] + ResponseOptions17)

    question18 = 'I am able to wander off into my own thoughts while doing a routine task, and then find a few minutes later that I have completed it.'
    ResponseOptions18 = ['True', 'False']
    questions.append([question18] + ResponseOptions18)

    question19 = 'I can sometimes recollect certain past experiences in my life with such clarity and vividness that it is like living them again or almost so.'
    ResponseOptions19 = ['True', 'False']
    questions.append([question19] + ResponseOptions19)

    question20 = 'Things that might seem meaningless to others often make sense to me.'
    ResponseOptions20 = ['True', 'False']
    questions.append([question20] + ResponseOptions20)

    question21 = 'While acting in a play, I think I could really feel the emotions of the character and “become” her/him for the time being, forgetting both myself and the audience.'
    ResponseOptions21 = ['True', 'False']
    questions.append([question21] + ResponseOptions21)

    question22 = "My thoughts often don't occur as words but as visual images."
    ResponseOptions22 = ['True', 'False']
    questions.append([question22] + ResponseOptions22)

    question23 = 'I often take delight in small things (like; the five-pointed star shape that appears when you cut an apple across the core or the colors in soap bubbles).'
    ResponseOptions23 = ['True', 'False']
    questions.append([question23] + ResponseOptions23)

    question24 = 'When listening to organ music or other powerful music I sometimes feel as if I am being lifted into the sky.'
    ResponseOptions24 = ['True', 'False']
    questions.append([question24] + ResponseOptions24)

    question25 = 'Sometimes I can change noise into music by the way I listen to it.'
    ResponseOptions25 = ['True', 'False']
    questions.append([question25] + ResponseOptions25)

    question26 = 'Some of my most vivid memories are called up by scents or sounds.'
    ResponseOptions26 = ['True', 'False']
    questions.append([question26] + ResponseOptions26)

    question27 = 'Certain pieces of music remind me of pictures or moving patterns of color.'
    ResponseOptions27 = ['True', 'False']
    questions.append([question27] + ResponseOptions27)

    question28 = 'I often know what someone is going to say before he/she/they says it.'
    ResponseOptions28 = ['True', 'False']
    questions.append([question28] + ResponseOptions28)

    question29 = "I often have 'physical memories'; for example, after I've been swimming, I may feel as if I'm in the water."
    ResponseOptions29 = ['True', 'False']
    questions.append([question29] + ResponseOptions29)

    question30 = 'The sound of a voice can be so fascinating to me that I can just go on listening to it.'
    ResponseOptions30 = ['True', 'False']
    questions.append([question30] + ResponseOptions30)

    question31 = 'At times I somehow feel the presence of someone who is not physically there.'
    ResponseOptions31 = ['True', 'False']
    questions.append([question31] + ResponseOptions31)

    question32 = 'Sometimes thoughts and images come to me without the slightest effort on my part.'
    ResponseOptions32 = ['True', 'False']
    questions.append([question32] + ResponseOptions32)

    question33 = 'I find that different odors have different colors.'
    ResponseOptions33 = ['True', 'False']
    questions.append([question33] + ResponseOptions33)

    question34 = 'I can be deeply moved by a sunset.'
    ResponseOptions34 = ['True', 'False']
    questions.append([question34] + ResponseOptions34)

    submitButton = Button('submit', 'tellegen', 'Submit', -1, 0) # submit button
    responses = [] # for storing answers to each question

    # iterate over each question and display to user
    for i, question in enumerate(questions):

        response = None

        if i == 0:
            multiLineMessage(telleganScaleText, mediumFont, win)
            pg.display.flip()
            waitKey(pg.K_SPACE)
            pg.mouse.set_visible(True)

        # draw the question and return how far down the screen the text goes
        yPos = multiLineMessage(question[0], mediumFont, win)

        # create all of the options for this particular questions
        buttons = [submitButton]
        for i, question_option in enumerate(question):
            if i == 0:
                continue
            buttons.append(Button('option', 'tellegen', question_option, i, yPos))

        while response == None:
            win.fill(backgroundColor)
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE: # escape will exit the study
                        pg.quit()
                        sys.exit()
                elif event.type == pg.MOUSEBUTTONUP:
                    for i, button in enumerate(buttons):
                        if (button.coords[0] <= pg.mouse.get_pos()[0] <= button.coords[0] + button.coords[2]) \
                            and (button.coords[1] <= pg.mouse.get_pos()[1] <= button.coords[1] + button.coords[3]):
                            response = button.handleClick(buttons)

            # draw the question and return how far down the screen the text goes
            multiLineMessage(question[0], mediumFont, win)

            # draw the submit button and the checkboxes for this questions
            submitButton.draw(win)
            for i, button in enumerate(buttons): 
                button.draw(win)
            pg.display.flip() 
        
        # add the user's response to the list of responses
        responses.append(response)
    
    # write all of the responses to a csv file with the questionnaire's name as the file name. 
    with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'tellegen_{subjectNumber}.csv'), mode = 'w', newline = '') as f:
        writer = csv.writer(f)
        header = ["Subject Number"] + [f'Q{i + 1}' for i in range(len(questions))]
        writer.writerow(header)
        assert(len(responses) == 34)
        writer.writerow([subjectNumber] + responses)
    return

def vhq(subjectNumber, win):
    # === VOICE HEARING QUESTIONNAIRE (VHQ) ===

    questions = []

    # 1
    q1 = "Sometimes I’ve thought I heard people say my name — like in a store when I walk past people I don’t know — but I know they didn’t really say my name, so I just go on."
    questions.append([q1, 'True', 'False'])

    # 2
    q2 = "Sometimes when I’m just about to fall asleep, I hear my name as if spoken aloud."
    questions.append([q2, 'True', 'False'])

    # 3
    q3 = "When I wake up in the morning but stay in bed for a few minutes, sometimes I hear my mother’s voice when she’s not there — like now when I’m living in the dorm. I hear her saying things like “Come on and get up” or “Don’t be late for school.” I’m used to it, and it doesn’t bother me."
    questions.append([q3, 'True', 'False'])

    # 4a
    q4a = "I hear a voice that’s kind of garbled — I can’t really tell what it says — sometimes just as I go to sleep."
    questions.append([q4a, 'True', 'False'])

    # 4b
    q4b = "I’ve had experiences of hearing something just as I’m going to sleep or waking up."
    questions.append([q4b, 'True', 'False'])

    # 5a
    q5a = "When I was little, I had an imaginary playmate. I remember really thinking I heard her voice when we talked."
    questions.append([q5a, 'True', 'False'])

    # 5b
    q5b = "When I had an imaginary playmate, I could actually hear their voice aloud."
    questions.append([q5b, 'True', 'False'])

    # 6
    q6 = "Every now and then — not very often — I think I hear my name on the radio."
    questions.append([q6, 'True', 'False'])

    # 7
    q7 = "Sometimes when I’m in the house all alone, I hear a voice call my name. It was scary at first, but now it isn’t. It’s just once — like ‘Sally!’ — kind of quick, like somebody’s calling me. I guess I know it’s really me, but it still sounds like a real voice."
    questions.append([q7, 'True', 'False'])

    # 8
    q8 = "Last summer, while hanging up clothes in the backyard, I suddenly heard my husband call my name from inside the house. It sounded loud and clear, like something was wrong — but he was outside and hadn’t called at all."
    questions.append([q8, 'True', 'False'])

    # 9
    q9 = "I’ve heard the doorbell or the phone ring when it didn’t."
    questions.append([q9, 'True', 'False'])

    # 10
    q10 = "I hear my thoughts aloud."
    questions.append([q10, 'True', 'False'])

    # 11
    q11 = "I’ve heard God’s voice — not just in my heart, but as a real voice."
    questions.append([q11, 'True', 'False'])

    # 12
    q12 = "When I’m driving in my car — particularly when I’m tired or worried — I hear my own voice from the backseat. It sounds soothing, like ‘It’ll be all right’ or ‘Just calm down.’"
    questions.append([q12, 'True', 'False'])

    # 13
    q13 = "I drive a lot at night for work. Sometimes when I’m tired, I hear sounds in the backseat like people talking — not clear, just words here and there. It scared me at first, but now I’m used to it. I think it happens because I’m tired and alone."
    questions.append([q13, 'True', 'False'])

    # 14
    q14 = "Almost every morning while I do my housework, I have a pleasant conversation with my dead grandmother. I talk to her and quite regularly hear her voice aloud."
    questions.append([q14, 'True', 'False'])

    # === Display Logic (same as your Tellegen function) ===

    submitButton = Button('submit', 'vhq', 'Submit', -1, 0)
    responses = []
    pg.mouse.set_visible(False)
    for i, question in enumerate(questions):
        response = None

        if i == 0:
            pg.mouse.set_visible(True)
            introText = "The following questions describe experiences some people have had involving hearing voices or sounds. Please answer each with 'True' or 'False' depending on whether or not you have experienced the situation, or if you have experienced an situation that is analagous to the one described."
            multiLineMessage(introText, mediumFont, win)
            pg.display.flip()
            waitKey(pg.K_SPACE)
            pg.mouse.set_visible(True)

        yPos = multiLineMessage(question[0], mediumFont, win)
        buttons = [submitButton]
        for j, opt in enumerate(question[1:]):
            buttons.append(Button('option', 'vhq', opt, j + 1, yPos))

        while response is None:
            win.fill(backgroundColor)
            for event in pg.event.get():
                if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                    pg.quit(); sys.exit()
                elif event.type == pg.MOUSEBUTTONUP:
                    for btn in buttons:
                        if (btn.coords[0] <= pg.mouse.get_pos()[0] <= btn.coords[0] + btn.coords[2]) and \
                           (btn.coords[1] <= pg.mouse.get_pos()[1] <= btn.coords[1] + btn.coords[3]):
                            response = btn.handleClick(buttons)

            multiLineMessage(question[0], mediumFont, win)
            submitButton.draw(win)
            for btn in buttons:
                btn.draw(win)
            pg.display.flip()

        responses.append(response)

    # === Save Responses ===
    out_path = os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'vhq_{subjectNumber}.csv')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Subject Number"] + [f'Q{i + 1}' for i in range(len(questions))])
        writer.writerow([subjectNumber] + responses)

    return

# contains questionnaire questions and displays questionnaire to the subject
def launay_slade(subjectNumber, win):

    # variables to hold all of the questions and their associated response options
    questions = []

    # question 1 text and response options
    question1 = 'Sometimes a passing thought will seem so real that it frightens me.'
    ResponseOptions1 = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    questions.append([question1] + ResponseOptions1)

    question2 = 'Sometimes my thoughts seem as real as actual events in my life.'
    ResponseOptions2 = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    questions.append([question2] + ResponseOptions2)

    question3 = 'No matter how much I try to concentrate on my work unrelated thoughts always creep into my mind.'
    ResponseOptions3 = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    questions.append([question3] + ResponseOptions3)

    question4 = "In the past I have had the experience of hearing a person's voice and then found that there was no one there."
    ResponseOptions4 = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    questions.append([question4] + ResponseOptions4)

    question5 = 'The sounds I hear in my daydreams are generally clear and distinct.'
    ResponseOptions5 = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    questions.append([question5] + ResponseOptions5)

    question6 = 'The people in my daydreams seem so true to life that I sometimes think they are.'
    ResponseOptions6 = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    questions.append([question6] + ResponseOptions6)

    question7 = 'In my daydreams I can hear the sound of a tune almost as clearly as if I were actually listening to it.'
    ResponseOptions7 = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    questions.append([question7] + ResponseOptions7)

    question8 = 'I often hear a voice speaking my thoughts aloud.'
    ResponseOptions8 = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    questions.append([question8] + ResponseOptions8)

    question9 = 'I have never been troubled by hearing voices in my head.'
    ResponseOptions9 = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    questions.append([question9] + ResponseOptions9)
    
    question10 = 'On occasions I have seen a person’s face in front of me when no one was in fact there.'
    ResponseOptions10 = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    questions.append([question10] + ResponseOptions10)

    question11 = 'I have never heard the voice of the Devil.'
    ResponseOptions11 = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    questions.append([question11] + ResponseOptions11)

    question12 = "In the past I have heard the voice of God speaking to me."
    ResponseOptions12 = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    questions.append([question12] + ResponseOptions12)

    submitButton = Button('submit', 'launay', 'Submit', -1, 0) # submit button
    responses = [] # for storing answers to each question

    # iterate over each question and display to user
    for i, question in enumerate(questions):
        
        if i == 0:
            pg.mouse.set_visible(True)
            multiLineMessage(launeyScaleText, mediumFont, win)
            pg.display.flip()
            waitKey(pg.K_SPACE)
            pg.mouse.set_visible(True)

        response = None

        # draw the question and return how far down the screen the text goes
        yPos = multiLineMessage(question[0], mediumFont, win)

        # create all of the options for this particular questions
        buttons = [submitButton]
        for i, question_option in enumerate(question):
            if i == 0:
                continue
            buttons.append(Button('option', 'launay', question_option, i, yPos))

        while response == None:

            win.fill(backgroundColor)
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE: # escape will exit the study
                        pg.quit()
                        sys.exit()
                elif event.type == pg.MOUSEBUTTONUP:
                    for i, button in enumerate(buttons):
                        if (button.coords[0] <= pg.mouse.get_pos()[0] <= button.coords[0] + button.coords[2]) \
                            and (button.coords[1] <= pg.mouse.get_pos()[1] <= button.coords[1] + button.coords[3]):
                            response = button.handleClick(buttons)

            # draw the question and return how far down the screen the text goes
            multiLineMessage(question[0], mediumFont, win)

            # draw the submit button and the questions
            submitButton.draw(win)
            for i, button in enumerate(buttons): 
                button.draw( win)
            pg.display.flip() 
        
        # add the user's response to the list of responses
        responses.append(response)
    
    # write the responses to a csv file with the questionnaire's name
    with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'launay_slade_{subjectNumber}.csv'), mode = 'w', newline = '') as f:
        writer = csv.writer(f)
        header = ["Subject Number"] + [f'Q{i + 1}' for i in range(len(questions))]
        writer.writerow(header)
        assert(len(responses) == 12)
        writer.writerow([subjectNumber] + [''.join([ch for ch in response if ch.isdigit()]) for response in responses])
    return

# contains questionnaire questions and displays questionnaire to the subject
def stanford_sleepiness_scale(sleepinessResponses, win, label=None):
    pg.mouse.set_visible(True)

    # variables to hold all of the questions and their associated response options
    questions = []

    # question 1 text and response options
    question1 = 'Please indicate your current level of sleepiness'
    ResponseOptions1 = ['1 - Feeling active and vital; alert; wide awake.', '2 - Functioning at a high level, but not at peak; able to concentrate.', '3 - Relaxed; awake; not at full alertness; responsive.', '4 - A little foggy; not at peak; let down.', '5 - Fogginess; beginning to lose interest in remaining awake; slowed down.', '6 - Sleepiness; prefer to be lying down; fighting sleep; woozy.', '7 - Almost in reverie; sleep onset soon; lost struggle to remain awake']
    questions.append([question1] + ResponseOptions1)

    submitButton = Button('submit', 'launay', 'Submit', -1, 0) # submit button
    responses = [] # for storing answers to each question

    # iterate over each question and display to user
    for i, question in enumerate(questions):
        
        response = None

        # draw the question and return how far down the screen the text goes
        yPos = multiLineMessage(question[0], mediumFont, win)

        # create all of the options for this particular questions
        buttons = [submitButton]
        for i, question_option in enumerate(question):
            if i == 0:
                continue
            buttons.append(Button('option', 'sleepiness', question_option, i, yPos))

        while response == None:

            win.fill(backgroundColor)
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE: # escape will exit the study
                        pg.quit()
                        sys.exit()
                elif event.type == pg.MOUSEBUTTONUP:
                    for i, button in enumerate(buttons):
                        if (button.coords[0] <= pg.mouse.get_pos()[0] <= button.coords[0] + button.coords[2]) \
                            and (button.coords[1] <= pg.mouse.get_pos()[1] <= button.coords[1] + button.coords[3]):
                            response = button.handleClick(buttons)

            # draw the question and return how far down the screen the text goes
            multiLineMessage(question[0], mediumFont, win)

            # draw the submit button and the questions
            submitButton.draw(win)
            for i, button in enumerate(buttons): 
                button.draw( win)
            pg.display.flip() 
        
        # add the user's response to the list of responses
        responses.append(response)
    
    # Store response with label if provided, otherwise use the response directly
    if label:
        sleepinessResponses.append(f"{label}: {responses[0]}")
    else:
        sleepinessResponses.append(responses[0])
    pg.mouse.set_visible(True)
    return

# contains questionnaire questions and displays questionnaire to the subject
def flow_state_scale(subjectNumber, win):

    # variables to hold all of the questions and their associated response options
    questions = []

    dfs_instructions = 'Please answer the following questions in relation to your experience on general tasks. These questions relate to the thoughts and feelings you may experience while completing various tasks in your life. You may experience these characteristics some of the time, all of the time, or none of the time. There are no right or wrong answers. Think about how often you experience each characteristic during your typical tasks, and then circle the number that best matches your experience.\n\n Press the spacebar to begin.'

    responseOptions = ['1 - Strongly disagree', '2', '3 - Neither agree nor disagree', '4', '5 - Strongly agree']

    question1 = 'I feel I am competent enough to meet the demands of the situation'
    questions.append([question1] + responseOptions)

    question2 = 'I do things spontaneously and automatically without having to think'
    questions.append([question2] + responseOptions)

    question3 = 'I have a strong sense of what I want to do'
    questions.append([question3] + responseOptions)

    question4 = 'I have a good idea about how well I am doing while I am involved in the task/activity'
    questions.append([question4] + responseOptions)

    question5 = 'I am completely focused on the task at hand'
    questions.append([question5] + responseOptions)

    question6 = 'I have a feeling of total control over what I am doing'
    questions.append([question6] + responseOptions)

    question7 = 'I am not worried about what others may be thinking of me'
    questions.append([question7] + responseOptions)

    question8 = 'The way time passes seems to be different from normal'
    questions.append([question8] + responseOptions)

    question9 = 'The experience is extremely rewarding'
    questions.append([question9] + responseOptions)

    submitButton = Button('submit', 'launay', 'Submit', -1, 0) # submit button
    responses = [] # for storing answers to each question

    # iterate over each question and display to user
    for i, question in enumerate(questions):
        
        if i == 0:
            pg.mouse.set_visible(False)
            multiLineMessage(dfs_instructions, mediumFont, win)
            pg.display.flip()
            waitKey(pg.K_SPACE)
            pg.mouse.set_visible(True)

        response = None

        # draw the question and return how far down the screen the text goes
        yPos = multiLineMessage(question[0], mediumFont, win)

        # create all of the options for this particular questions
        buttons = [submitButton]
        for i, question_option in enumerate(question):
            if i == 0:
                continue
            buttons.append(Button('option', 'launay', question_option, i, yPos))

        while response == None:

            win.fill(backgroundColor)
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE: # escape will exit the study
                        pg.quit()
                        sys.exit()
                elif event.type == pg.MOUSEBUTTONUP:
                    for i, button in enumerate(buttons):
                        if (button.coords[0] <= pg.mouse.get_pos()[0] <= button.coords[0] + button.coords[2]) \
                            and (button.coords[1] <= pg.mouse.get_pos()[1] <= button.coords[1] + button.coords[3]):
                            response = button.handleClick(buttons)

            # draw the question and return how far down the screen the text goes
            multiLineMessage(question[0], mediumFont, win)

            # draw the submit button and the questions
            submitButton.draw(win)
            for i, button in enumerate(buttons): 
                button.draw( win)
            pg.display.flip() 
        
        # add the user's response to the list of responses
        responses.append(response)
    
    # write the responses to a csv file with the questionnaire's name
    with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'flow_state_scale_{subjectNumber}.csv'), mode = 'w', newline = '') as f:
        writer = csv.writer(f)
        header = ["Subject Number"] + [f'Q{i + 1}' for i in range(len(questions))]
        assert(len(responses) == 9)
        writer.writerow(header)
        writer.writerow([subjectNumber] + [''.join([ch for ch in response if ch.isdigit()]) for response in responses])
    pg.mouse.set_visible(True)
    return

# contains questionnaire questions and displays questionnaire to the subject
def dissociative_experiences(subjectNumber, win):

    # variables to hold all of the questions and their associated response options
    questions = []

    # question 1 text and response options
    question1 = "Some people have the experience of driving a car and suddenly realizing that they don't remember what has happened during all or part of the trip. Select a box to show what percentage of the time this happens to you."
    ResponseOptions1 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question1] + ResponseOptions1)

    question2 = 'Some people find that sometimes they are listening to someone talk and they suddenly realize that they did not hear all or part of what was said. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions2 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question2] + ResponseOptions2)

    question3 = 'Some people have the experience of finding themselves in a place and having no idea how they got there. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions3 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question3] + ResponseOptions3)

    question4 = "Some people have the experience of finding themselves dressed in clothes that they don't remember putting on. Select a box to show what percentage of the time this happens to you."
    ResponseOptions4 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question4] + ResponseOptions4)

    question5 = 'Some people have the experience of finding new things among their belongings that they do not remember buying. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions5 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question5] + ResponseOptions5)

    question6 = 'Some people sometimes find that they are approached by people that they do not know who call them by another name or insist that they have met them before. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions6 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question6] + ResponseOptions6)

    question7 = 'Some people sometimes have the experience of feeling as though they are standing next to themselves or watching themselves do something as if they were looking at another person. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions7 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question7] + ResponseOptions7)

    question8 = 'Some people are told that they sometimes do not recognize friends or family members. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions8 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question8] + ResponseOptions8)

    question9 = 'Some people find that they have no memory for some important events in their lives (for example, a wedding or graduation). Select a box to show what percentage of the time this happens to you.'
    ResponseOptions9 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question9] + ResponseOptions9)
    
    question10 = 'Some people have the experience of being accused of lying when they do not think that they have lied. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions10 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question10] + ResponseOptions10)

    question11 = 'Some people have the experience of looking in a mirror and not recognizing themselves. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions11 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question11] + ResponseOptions11)

    question12 = "Some people sometimes have the experience of feeling that other people, objects, and the world around them are not real. Select a box to show what percentage of the time this happens to you."
    ResponseOptions12 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question12] + ResponseOptions12)

    question13 = 'Some people sometimes have the experience of feeling that their body does not belong to them. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions13 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question13] + ResponseOptions13)

    question14 = 'Some people have the experience of sometimes remembering a past event so vividly that they feel as if they were reliving that event. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions14 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question14] + ResponseOptions14)

    question15 = 'Some people have the experience of not being sure whether things that they remember happening really did happen or whether they just dreamed them. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions15 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question15] + ResponseOptions15)

    question16 = 'Some people have the experience of being in a familiar place but finding it strange and unfamiliar. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions16 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question16] + ResponseOptions16)

    question17 = 'Some people find that when they are watching television or a movie they become so absorbed in the story that they are unaware of other events happening around them. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions17 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question17] + ResponseOptions17)

    question18 = 'Some people sometimes find that they become so involved in a fantasy or daydream that it feels as though it were really happening to them. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions18 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question18] + ResponseOptions18)

    question19 = 'Some people find that they are sometimes able to ignore pain. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions19 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question19] + ResponseOptions19)

    question20 = 'Some people find that they sometimes sit staring off into space, thinking of nothing, and are not aware of the passage of time. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions20 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question20] + ResponseOptions20)

    question21 = 'Some people sometimes find that when they are alone they talk out loud to themselves. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions21 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question21] + ResponseOptions21)

    question22 = "Some people find that in one situation they may act so differently compared with another situation that they feel almost as if they were different people. Select a box to show what percentage of the time this happens to you."
    ResponseOptions22 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question22] + ResponseOptions22)

    question23 = 'Some people sometimes find that in certain situations they are able to do things with amazing ease and spontaneity that would usually be difficult for them (for example, sports, work, social situations, etc.). Select a box to show what percentage of the time this happens to you.'
    ResponseOptions23 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question23] + ResponseOptions23)

    question24 = 'Some people sometimes find that they cannot remember whether they have done something or have just thought about doing that thing (for example, not knowing whether they have just mailed a letter or have just thought about mailing it). Select a box to show what percentage of the time this happens to you.'
    ResponseOptions24 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question24] + ResponseOptions24)

    question25 = 'Some people find evidence that they have done things that they do not remember doing. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions25 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question25] + ResponseOptions25)

    question26 = 'Some people sometimes find writings, drawings, or notes among their belongings that they must have done but cannot remember doing. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions26 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question26] + ResponseOptions26)

    question27 = 'Some people find that they sometimes hear voices inside their head that tell them to do things or comment on things that they are doing. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions27 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question27] + ResponseOptions27)

    question28 = 'Some people sometimes feels as if they are looking at the world through a fog so that people or objects appear far away or unclear. Select a box to show what percentage of the time this happens to you.'
    ResponseOptions28 = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    questions.append([question28] + ResponseOptions28)

    submitButton = Button('submit', 'dissociative', 'Submit', -1, 0) # submit button
    responses = [] # for storing answers to each question

    # iterate over each question and display to user
    for i, question in enumerate(questions):

        # instructions
        if i == 0:
            pg.mouse.set_visible(True)
            multiLineMessage(dissociativeExperiencesText, mediumFont, win)
            pg.display.flip()
            waitKey(pg.K_SPACE)
            pg.mouse.set_visible(True)

        # draw the question and return how far down the screen the text goes
        yPos = multiLineMessage(question[0], mediumFont, win)

        response = None

        # create all of the options for this particular questions
        buttons = [submitButton]
        for i, question_option in enumerate(question):
            if i == 0:
                continue
            buttons.append(Button('option', 'dissociative', question_option, i - 1, yPos))

        while response == None:
            win.fill(backgroundColor)
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE: # escape will exit the study
                        pg.quit()
                        sys.exit()
                elif event.type == pg.MOUSEBUTTONUP:
                    for i, button in enumerate(buttons):
                        if (button.coords[0] <= pg.mouse.get_pos()[0] <= button.coords[0] + button.coords[2]) \
                            and (button.coords[1] <= pg.mouse.get_pos()[1] <= button.coords[1] + button.coords[3]):
                            response = button.handleClick(buttons)

            # draw the question
            multiLineMessage(question[0], mediumFont, win)

            # draw the submit button and display each checkbox
            submitButton.draw(win)
            for i, button in enumerate(buttons): 
                button.draw( win)
            pg.display.flip() 

        # add the user's response to this question to the list of responses
        responses.append(response)

    # write the questionnaire responses to a csv file with the questionaire's name
    with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'dissociative_experiences_{subjectNumber}.csv'), mode = 'w', newline = '') as f:
        writer = csv.writer(f)
        header = ["Subject Number"] + [f'Q{i + 1}' for i in range(len(questions))]
        writer.writerow(header)
        assert(len(responses) == 28)
        writer.writerow([subjectNumber] + [''.join([ch for ch in response if ch.isdigit()]) for response in responses])
    return


# contains questionnaire questions and displays questionnaire to the subject
def bais_v(subjectNumber, win):

    questions = []

    bais_v_instructions = 'For the following questions please do the following: Read the item and consider whether you can imagine the described sound in your head. Then rate the vividness of the imagined sound in your head on a scale from 1 (no mental image) to 7 (as vivid as the actual sound).\n\nPress the spacebar to begin.'

    responseOptions = ['1 - No Imagined Sound', '2', '3', '4 - Somewhat Vivid', '5', '6', '7 - Extremely Vivid']

    questions.append(['For the first item, consider the beginning of the song “Happy Birthday.”\nThe sound of a trumpet beginning the piece.'] + responseOptions)
    questions.append(['For the next item, consider ordering something over the phone.\nThe voice of an elderly clerk assisting you.'] + responseOptions)
    questions.append(['For the next item, consider being at the beach.\nThe sound of the waves crashing against nearby rocks.'] + responseOptions)
    questions.append(['For the next item, consider going to a dentist appointment.\nThe loud sound of the dentist’s drill.'] + responseOptions)
    questions.append(['For the next item, consider being present at a jazz club.\nThe sound of a saxophone solo.'] + responseOptions)
    questions.append(['For the next item, consider being at a live baseball game.\nThe cheer of the crowd as a player hits the ball.'] + responseOptions)
    questions.append(['For the next item, consider attending a choir rehearsal.\nThe sound of an all-children’s choir singing the first verse of a song.'] + responseOptions)
    questions.append(['For the next item, consider attending an orchestral performance of Beethoven’s Fifth.\nThe sound of the ensemble playing.'] + responseOptions)
    questions.append(['For the next item, consider listening to a rain storm.\nThe sound of gentle rain.'] + responseOptions)
    questions.append(['For the next item, consider attending classes.\nThe slow-paced voice of your English teacher.'] + responseOptions)
    questions.append(['For the next item, consider seeing a live opera performance.\nThe voice of an opera singer in the middle of a verse.'] + responseOptions)
    questions.append(['For the next item, consider attending a new tap-dance performance.\nThe sound of tap-shoes on the stage.'] + responseOptions)
    questions.append(['For the next item, consider a kindergarten class.\nThe voice of the teacher reading a story to the children.'] + responseOptions)
    questions.append(['For the next item, consider driving in a car.\nThe sound of an upbeat rock song on the radio.'] + responseOptions)

    submitButton = Button('submit', 'bais_v', 'Submit', -1, 0) # submit button
    responses = [] # for storing answers to each question

    for i, question in enumerate(questions):

        if i == 0:
            pg.mouse.set_visible(False)
            multiLineMessage(bais_v_instructions, mediumFont, win)
            pg.display.flip()
            waitKey(pg.K_SPACE)
            pg.mouse.set_visible(True)

        response = None
        yPos = multiLineMessage(question[0], mediumFont, win)

        buttons = [submitButton]
        for i, question_option in enumerate(question):
            if i == 0:
                continue
            buttons.append(Button('option', 'bais_v', question_option, i, yPos))

        while response == None:

            win.fill(backgroundColor)
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        pg.quit()
                        sys.exit()
                elif event.type == pg.MOUSEBUTTONUP:
                    for i, button in enumerate(buttons):
                        if (button.coords[0] <= pg.mouse.get_pos()[0] <= button.coords[0] + button.coords[2]) \
                            and (button.coords[1] <= pg.mouse.get_pos()[1] <= button.coords[1] + button.coords[3]):
                            response = button.handleClick(buttons)

            multiLineMessage(question[0], mediumFont, win)

            submitButton.draw(win)
            for i, button in enumerate(buttons):
                button.draw(win)
            pg.display.flip()

        responses.append(response)

    with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'bais_v_{subjectNumber}.csv'), mode = 'w', newline = '') as f:
        writer = csv.writer(f)
        header = ["Subject Number"] + [f'Q{i + 1}' for i in range(len(questions))]
        writer.writerow(header)
        assert(len(responses) == 14)
        writer.writerow([subjectNumber] + [''.join([ch for ch in response if ch.isdigit()]) for response in responses])
    pg.mouse.set_visible(True)
    return


# contains questionnaire questions and displays questionnaire to the subject
def bais_c(subjectNumber, win):

    questions = []

    bais_c_instructions = 'For the following pairs of items you are asked to do the following: Read the first item (marked “a”) and consider whether you think of an image of the described sound in your head. Then read the second item (marked “b”) and consider how easily you could change your image of the first sound to that of the second sound and hold this image. Rate how easily you could make this change using the “Ease of Change Rating Scale.” If no images are generated, give a rating of 1. Please read “a” first and “b” second for each pair.\n\nPress the spacebar to begin.'

    responseOptions = ['1 - No Imagined Sound', '2', '3', '4 - Somewhat Vivid', '5', '6', '7 - Extremely Vivid']

    questions.append(['For the first pair, consider attending a choir rehearsal.\na. The sound of an all-children’s choir singing the first verse of a song.\nb. An all-adults’ choir now sings the second verse of the song.'] + responseOptions)
    questions.append(['For the next pair, consider being present at a jazz club.\na. The sound of a saxophone solo.\nb. The saxophone is now accompanied by a piano.'] + responseOptions)
    questions.append(['For the next pair, consider listening to a rain storm.\na. The sound of gentle rain.\nb. The gentle rain turns into a violent thunderstorm.'] + responseOptions)
    questions.append(['For the next pair, consider driving in a car.\na. The sound of an upbeat rock song on the radio.\nb. The song is now masked by the sound of the car coming to a screeching halt.'] + responseOptions)
    questions.append(['For the next pair, consider ordering something over the phone.\na. The voice of an elderly clerk assisting you.\nb. The elderly clerk leaves and the voice of a younger clerk is now on the line.'] + responseOptions)
    questions.append(['For the next pair, consider seeing a live opera performance.\na. The voice of an opera singer in the middle of a verse.\nb. The opera singer now reaches the end of the piece and holds the final note.'] + responseOptions)
    questions.append(['For the next pair, consider going to a dentist appointment.\na. The loud sound of the dentist’s drill.\nb. The drill stops and you can now hear the soothing voice of the receptionist.'] + responseOptions)
    questions.append(['For the next pair, consider the beginning of the song “Happy Birthday.”\na. The sound of a trumpet beginning the piece.\nb. The trumpet stops and a violin continues the piece.'] + responseOptions)
    questions.append(['For the next pair, consider attending an orchestral performance of Beethoven’s Fifth.\na. The sound of the ensemble playing.\nb. The ensemble stops but the sound of a piano solo is present.'] + responseOptions)
    questions.append(['For the next pair, consider attending a new tap-dance performance.\na. The sound of tap-shoes on the stage.\nb. The sound of the shoes speeds up and gets louder.'] + responseOptions)
    questions.append(['For the next pair, consider being at a live baseball game.\na. The cheer of the crowd as a player hits the ball.\nb. Now the crowd boos as the fielder catches the ball.'] + responseOptions)
    questions.append(['For the next pair, consider a kindergarten class.\na. The voice of the teacher reading a story to the children.\nb. The teacher stops reading for a minute to talk to another teacher.'] + responseOptions)
    questions.append(['For the next pair, consider attending classes.\na. The slow-paced voice of your English teacher.\nb. The pace of the teacher’s voice gets faster at the end of class.'] + responseOptions)
    questions.append(['For the next pair, consider being at the beach.\na. The sound of the waves crashing against nearby rocks.\nb. The waves are now drowned out by the loud sound of a boat’s horn out at sea.'] + responseOptions)

    submitButton = Button('submit', 'bais_c', 'Submit', -1, 0) # submit button
    responses = [] # for storing answers to each question

    for i, question in enumerate(questions):

        if i == 0:
            pg.mouse.set_visible(False)
            multiLineMessage(bais_c_instructions, mediumFont, win)
            pg.display.flip()
            waitKey(pg.K_SPACE)
            pg.mouse.set_visible(True)

        response = None
        yPos = multiLineMessage(question[0], mediumFont, win)

        buttons = [submitButton]
        for i, question_option in enumerate(question):
            if i == 0:
                continue
            buttons.append(Button('option', 'bais_c', question_option, i, yPos))

        while response == None:

            win.fill(backgroundColor)
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        pg.quit()
                        sys.exit()
                elif event.type == pg.MOUSEBUTTONUP:
                    for i, button in enumerate(buttons):
                        if (button.coords[0] <= pg.mouse.get_pos()[0] <= button.coords[0] + button.coords[2]) \
                            and (button.coords[1] <= pg.mouse.get_pos()[1] <= button.coords[1] + button.coords[3]):
                            response = button.handleClick(buttons)

            multiLineMessage(question[0], mediumFont, win)

            submitButton.draw(win)
            for i, button in enumerate(buttons):
                button.draw(win)
            pg.display.flip()

        responses.append(response)

    with open(os.path.join(os.path.dirname(__file__), 'results', subjectNumber, f'bais_c_{subjectNumber}.csv'), mode = 'w', newline = '') as f:
        writer = csv.writer(f)
        header = ["Subject Number"] + [f'Q{i + 1}' for i in range(len(questions))]
        writer.writerow(header)
        assert(len(responses) == 14)
        writer.writerow([subjectNumber] + [''.join([ch for ch in response if ch.isdigit()]) for response in responses])
    pg.mouse.set_visible(True)
    return


def main(subjectNumber, win):

    tellegen(subjectNumber, win)
    vhq(subjectNumber, win)
    launay_slade(subjectNumber, win)
    dissociative_experiences(subjectNumber, win)
    bais_v(subjectNumber, win)
    bais_c(subjectNumber, win)
    pg.mouse.set_visible(True)
