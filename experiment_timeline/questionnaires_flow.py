"""
Questionnaires Flow Subtimeline
===============================
Handles all questionnaire administration including:
- Tellegen Absorption Scale
- Launay-Slade Hallucination Scale  
- Dissociative Experiences Scale
- Stanford Sleepiness Scale
- Flow State Scale
- BAIS-V/BAIS-C
- VHQ

Uses displayEngine for all rendering - no dependency on questionnaires.py
"""

import os
import sys
import csv
import math
import pygame as pg
from datetime import datetime

# Add parent directory for imports
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE_DIR)
sys.path.insert(0, os.path.join(_BASE_DIR, 'experiment_helpers'))
sys.path.insert(0, os.path.join(_BASE_DIR, 'utils'))

from utils.displayEngine import (
    Screen, TextRenderer, TextInput, InputMode,
    Colors, TextStyle, TextAlign,
)
from utils.eventLogger import ScreenEventLogger
from experiment_helpers.text_blocks.questionnairesTextBlocks import (
    telleganScaleIntro, launeyScaleIntro, dissociativeExperiencesIntro,
    flowStateIntro, vhqIntro, baisVIntro, baisCIntro, questionnairesIntro
)


# =============================================================================
# GENERIC QUESTIONNAIRE RENDERING
# =============================================================================

class QuestionnaireOption:
    """A clickable option button for questionnaire responses."""
    
    def __init__(
        self,
        text: str,
        x: int,
        y: int,
        size: int,
        font_size: int,
        max_text_width: int = 0,
    ):
        self.text = text
        self.rect = pg.Rect(x, y, size, size)
        self.font_size = font_size
        self.max_text_width = max_text_width
        self.selected = False
    
    def draw(self, win: pg.Surface) -> None:
        """Draw the option checkbox and label.  Darkens on hover (only if not selected)."""
        mouse_pos = pg.mouse.get_pos()
        hovered = self.rect.collidepoint(mouse_pos)

        if self.selected:
            # Selected state: solid color, no hover effect
            color = Colors.RED.to_tuple()
        else:
            # Unselected: apply hover darkening
            base = Colors.WHITE
            color = base.darken(0.85).to_tuple() if hovered else base.to_tuple()
        pg.draw.rect(win, color, self.rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), self.rect, 2)
        
        font = pg.font.SysFont("times new roman", self.font_size)
        text_x = self.rect.right + 10
        text_y = self.rect.top - 2
        
        # Wrap text if max_text_width is set and text is too wide
        if self.max_text_width > 0:
            words = self.text.split()
            lines = []
            current_line = []
            indent = "   "  # Indent for wrapped lines
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                test_surf = font.render(test_line, True, Colors.BLACK.to_tuple())
                if test_surf.get_width() <= self.max_text_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw wrapped lines
            line_height = int(self.font_size * 1.15)
            for i, line in enumerate(lines):
                prefix = indent if i > 0 else ""
                line_surf = font.render(prefix + line, True, Colors.BLACK.to_tuple())
                win.blit(line_surf, (text_x, text_y + i * line_height))
        else:
            text_surface = font.render(self.text, True, Colors.BLACK.to_tuple())
            win.blit(text_surface, (text_x, text_y))
    
    def contains_point(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


def _questionnaire_option_style(questionnaire_name: str, current_h: int) -> tuple[int, float]:
    """Return (font_size, row_spacing_scalar) matching the old code's proportions."""
    base_font = max(14, current_h // 20)
    font_size = base_font

    if questionnaire_name == 'tellegen':
        scalar = 1.75
    elif questionnaire_name == 'launay_slade':
        scalar = 1.4
    elif questionnaire_name == 'dissociative_experiences':
        scalar = 1.5
    elif questionnaire_name == 'sleepiness':
        scalar = 1.3
        font_size = int(0.85 * base_font)
    elif questionnaire_name == 'vhq':
        scalar = 1.4
    elif 'bais' in questionnaire_name:
        scalar = 1.3
        # Keep standard font size for checkbox sizing, anchors wrap if needed
    elif questionnaire_name == 'flow_state_scale':
        scalar = 1.5
    else:
        scalar = 1.5

    return font_size, scalar


def _precompute_option_slots(
    questionnaire_name: str,
    win: pg.Surface,
    y_pos_question_fixed: int,
    max_options: int,
) -> list[dict]:
    """Create stable checkbox positions based on worst-case option count.

    The slots are reused for every question so options never shift.
    Matches the old code's ``_precompute_option_slots`` logic exactly.
    """
    screen = Screen(win)
    current_w, current_h = screen.width, screen.height
    font_size, scalar = _questionnaire_option_style(questionnaire_name, current_h)

    buffer = current_h // 40  # Reduced from //20 (5%) to //40 (2.5%)
    button_size = max(int(0.015 * min(current_w, current_h)), font_size)

    y_start = int(y_pos_question_fixed + buffer)
    
    # Options end at 0.82 to leave buffer above submit button (at 0.88-0.90)
    if questionnaire_name in ('dissociative_experiences', 'bais_c'):
        y_end = int(0.80 * current_h) - font_size  # More buffer for these
    else:
        y_end = int(0.82 * current_h) - font_size
    
    if y_end <= y_start:
        y_start = int(0.30 * current_h)
        y_end = int(0.82 * current_h) - font_size

    available_height = max(1, y_end - y_start)

    desired_row_step = max(1, int(scalar * font_size))
    min_row_step = max(1, int(1.05 * font_size))

    max_rows_one_col = max(1, 1 + (available_height // max(1, desired_row_step)))
    n_cols = 1 if max_options <= max_rows_one_col else 2

    rows_per_col = max(1, math.ceil(max_options / n_cols))
    if rows_per_col > 1:
        row_step_fit = max(1, available_height // (rows_per_col - 1))
    else:
        row_step_fit = desired_row_step
    row_step = max(min_row_step, min(desired_row_step, row_step_fit))

    x_left = int(0.05 * current_w)
    x_right = int(0.05 * current_w + 0.45 * current_w)
    
    # Center columns when there are 2
    if n_cols == 2:
        # Each column is about 45% wide, total 90% of screen
        # Center by adjusting left margin
        col_width = int(0.45 * current_w)
        total_width = 2 * col_width
        left_margin = (current_w - total_width) // 2
        x_left = left_margin
        x_right = left_margin + col_width
    
    left_count = max_options if n_cols == 1 else math.ceil(max_options / 2)
    
    # Calculate max text width for wrapping anchors
    # Leave room for checkbox (button_size + 10px gap) and padding
    if n_cols == 2:
        col_width = int(0.45 * current_w)
        max_text_width = col_width - button_size - 30  # padding between columns
    else:
        max_text_width = int(0.85 * current_w) - button_size - 20

    slots: list[dict] = []
    for idx in range(max_options):
        if n_cols == 1 or idx < left_count:
            x = x_left
            row = idx
        else:
            x = x_right
            row = idx - left_count
        y = int(y_start + row * row_step)
        slots.append({
            'x': x,
            'y': y,
            'button_size': button_size,
            'font_size': font_size,
            'max_text_width': max_text_width,
        })
    return slots


def _worst_case_question_bottom_y(
    questions: list[tuple[str, list[str]]],
    win: pg.Surface,
) -> int:
    """Render every question text off-screen and return the maximum bottom y."""
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    question_style = TextStyle(
        font_size=screen.scaled_font_size(20),
        color=Colors.BLACK,
        align=TextAlign.LEFT,
    )
    max_y = 0
    for q_text, _opts in questions:
        screen.fill()
        y = text_renderer.draw_text_block(
            q_text,
            rel_x=0.05,
            rel_y=0.05,
            max_width=screen.abs_x(0.9),
            style=question_style,
        )
        if y > max_y:
            max_y = y
    return max_y


def _run_single_question(
    win: pg.Surface,
    question_text: str,
    options: list[str],
    questionnaire_name: str,
    precomputed_slots: list[dict] | None = None,
    screen_logger: ScreenEventLogger | None = None,
    question_index: int = 0,
) -> str:
    """Display a single question and return the selected response.

    If *precomputed_slots* is provided, the option buttons use those
    fixed positions (so they never move between questions).
    """
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    current_w, current_h = screen.width, screen.height

    pg.mouse.set_visible(True)

    # Sizing
    font_size, scalar = _questionnaire_option_style(questionnaire_name, current_h)
    button_size = max(int(0.015 * min(current_w, current_h)), font_size)

    question_style = TextStyle(
        font_size=screen.scaled_font_size(20),
        color=Colors.BLACK,
        align=TextAlign.LEFT,
    )

    # Build option widgets from precomputed slots (stable) or compute them
    n_options = len(options)
    option_widgets: list[QuestionnaireOption] = []

    if precomputed_slots:
        for i, opt_text in enumerate(options):
            s = precomputed_slots[i]
            option_widgets.append(
                QuestionnaireOption(opt_text, s['x'], s['y'], s['button_size'], s['font_size'], 
                                   s.get('max_text_width', 0))
            )
    else:
        # Fallback: compute per-question (old behaviour for standalone calls)
        screen.fill()
        y_after_question = text_renderer.draw_text_block(
            question_text, rel_x=0.05, rel_y=0.05,
            max_width=screen.abs_x(0.9), style=question_style,
        )
        slots = _precompute_option_slots(questionnaire_name, win, y_after_question, n_options)
        for i, opt_text in enumerate(options):
            s = slots[i]
            option_widgets.append(
                QuestionnaireOption(opt_text, s['x'], s['y'], s['button_size'], s['font_size'],
                                   s.get('max_text_width', 0))
            )
    
    # Submit button (larger size)
    submit_font_size = int(0.85 * max(18, current_h // 18))
    submit_font = pg.font.SysFont("times new roman", submit_font_size)
    submit_surf = submit_font.render("Submit", True, Colors.BLACK.to_tuple())
    padding_x = int(0.03 * current_w)
    padding_y = int(0.015 * current_h)
    submit_width = max(int(0.12 * current_w), submit_surf.get_width() + 2 * padding_x)
    submit_height = max(int(0.06 * current_h), submit_surf.get_height() + 2 * padding_y)
    
    # Determine submit button Y position - more buffer for some questionnaires
    if questionnaire_name in ('dissociative_experiences', 'bais_c'):
        submit_y = int(0.90 * current_h)
    else:
        submit_y = int(0.88 * current_h)
    
    submit_rect = pg.Rect(
        (current_w - submit_width) // 2,
        submit_y,
        submit_width,
        submit_height,
    )
    
    selected_idx = None
    
    while True:
        screen.fill()
        
        # Draw question
        text_renderer.draw_text_block(
            question_text,
            rel_x=0.05,
            rel_y=0.05,
            max_width=screen.abs_x(0.9),
            style=question_style,
        )
        
        # Draw options
        for widget in option_widgets:
            widget.draw(win)
        
        # Draw submit button
        mouse_pos = pg.mouse.get_pos()
        if submit_rect.collidepoint(mouse_pos):
            btn_col = Colors.LIGHT_GRAY.to_tuple()
        else:
            btn_col = Colors.WHITE.to_tuple()
        pg.draw.rect(win, btn_col, submit_rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), submit_rect, 3)
        submit_surf = submit_font.render("Submit", True, Colors.BLACK.to_tuple())
        win.blit(submit_surf, submit_surf.get_rect(center=submit_rect.center))
        
        screen.update()
        
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()
            
            elif event.type == pg.MOUSEBUTTONUP:
                pos = pg.mouse.get_pos()
                
                # Check option clicks
                for i, widget in enumerate(option_widgets):
                    if widget.contains_point(pos):
                        # Deselect all others
                        for w in option_widgets:
                            w.selected = False
                        widget.selected = True
                        selected_idx = i
                        if screen_logger:
                            screen_logger.log_event('option_selected', f'Q{question_index+1}_option{i}')
                        break
                
                # Check submit button
                if submit_rect.collidepoint(pos) and selected_idx is not None:
                    if screen_logger:
                        screen_logger.log_event('submit_clicked', f'Q{question_index+1}')
                    return options[selected_idx]


def _run_questionnaire(
    win: pg.Surface,
    subject_number: str,
    questionnaire_name: str,
    questions: list[tuple[str, list[str]]],
    intro_text: str | None = None,
    save_filename: str | None = None,
    extract_numeric: bool = False,
) -> list[str]:
    """
    Run a complete questionnaire and save results.

    Option button positions are precomputed using the worst-case question
    height so that buttons never move between questions.
    """
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    # Event logging
    results_dir = os.path.join(_BASE_DIR, 'results', subject_number)
    screen_logger = ScreenEventLogger(f'questionnaire_{questionnaire_name}', results_dir, subject_number)
    
    # Show intro if provided
    if intro_text:
        pg.mouse.set_visible(False)
        style = TextStyle(
            font_size=screen.scaled_font_size(20),
            color=Colors.BLACK,
            align=TextAlign.LEFT,
            line_spacing=1.1,  # Tighter line spacing for intro screens
        )
        
        waiting = True
        while waiting:
            screen.fill()
            text_renderer.draw_text_block(
                intro_text,
                rel_x=0.05,
                rel_y=0.05,
                max_width=screen.abs_x(0.9),
                style=style,
                auto_fit=True,
                rel_max_y=0.95,
            )
            screen.update()
            
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        pg.quit()
                        sys.exit()
                    elif event.key == pg.K_SPACE:
                        screen_logger.log_event('key_press', 'space_intro')
                        waiting = False
        
        pg.mouse.set_visible(True)
    
    # --- precompute stable option positions (worst-case) ---
    max_options = max(len(opts) for _, opts in questions)
    y_pos_fixed = _worst_case_question_bottom_y(questions, win)
    option_slots = _precompute_option_slots(questionnaire_name, win, y_pos_fixed, max_options)
    
    # Run each question with precomputed slots
    responses = []
    for q_idx, (q_text, options) in enumerate(questions):
        response = _run_single_question(win, q_text, options, questionnaire_name, 
                                       precomputed_slots=option_slots,
                                       screen_logger=screen_logger,
                                       question_index=q_idx)
        responses.append(response)
    
    # Save event log
    screen_logger.save()
    
    # Save results
    os.makedirs(results_dir, exist_ok=True)
    
    filename = save_filename or f'{questionnaire_name}_{subject_number}.csv'
    filepath = os.path.join(results_dir, filename)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        header = ["Subject Number"] + [f'Q{i+1}' for i in range(len(questions))]
        writer.writerow(header)
        
        if extract_numeric:
            processed = [''.join(c for c in r if c.isdigit()) for r in responses]
        else:
            processed = responses
        
        writer.writerow([subject_number] + processed)
    
    return responses


# =============================================================================
# INDIVIDUAL QUESTIONNAIRES
# =============================================================================

def _tellegen(subject_number: str, win: pg.Surface) -> list[str]:
    """Run the Tellegen Absorption Scale (34 True/False questions)."""
    questions = [
        ('Sometimes I feel and experience things as I did when I was a child.', ['True', 'False']),
        ('I can be greatly moved by eloquent or poetic language.', ['True', 'False']),
        ('While watching a movie, a T.V. show, or a play, I may become so involved that I forget about myself and my surroundings and experience the story as if I were taking part in it.', ['True', 'False']),
        ('If I stare at a picture and then look away from it, I can sometimes "see" an image of the picture, almost as if I were looking at it.', ['True', 'False']),
        ('Sometimes I feel as if my mind could envelop the whole world.', ['True', 'False']),
        ('I like to watch cloud shapes change in the sky.', ['True', 'False']),
        ('If I wish, I can imagine (or daydream) some things so vividly that they hold my attention as a good movie or story does.', ['True', 'False']),
        ('I think I really know what some people mean when they talk about mystical experiences.', ['True', 'False']),
        ('I sometimes "step outside" my usual self and experience an entirely different state of being.', ['True', 'False']),
        ('Textures - such as wool, sand, wood - sometimes remind me of colors or music.', ['True', 'False']),
        ('Sometimes I experience things as if they were doubly real.', ['True', 'False']),
        ("When I listen to music, I can get so caught up in it that I don't notice anything else.", ['True', 'False']),
        ('If I wish, I can imagine that my body is so heavy that I could not move it if I wanted to.', ['True', 'False']),
        ('I can often somehow sense the presence of another person before I actually see or hear her/him/them.', ['True', 'False']),
        ('The crackle and flames of a wood fire stimulate my imagination.', ['True', 'False']),
        ('It is sometimes possible for me to be completely immersed in nature or in art and to feel as if my whole state of consciousness has somehow been temporarily altered.', ['True', 'False']),
        ('Different colors have distinctive and special meaning to me.', ['True', 'False']),
        ('I am able to wander off into my own thoughts while doing a routine task, and then find a few minutes later that I have completed it.', ['True', 'False']),
        ('I can sometimes recollect certain past experiences in my life with such clarity and vividness that it is like living them again or almost so.', ['True', 'False']),
        ('Things that might seem meaningless to others often make sense to me.', ['True', 'False']),
        ('While acting in a play, I think I could really feel the emotions of the character and "become" her/him for the time being, forgetting both myself and the audience.', ['True', 'False']),
        ("My thoughts often don't occur as words but as visual images.", ['True', 'False']),
        ('I often take delight in small things (like; the five-pointed star shape that appears when you cut an apple across the core or the colors in soap bubbles).', ['True', 'False']),
        ('When listening to organ music or other powerful music I sometimes feel as if I am being lifted into the sky.', ['True', 'False']),
        ('Sometimes I can change noise into music by the way I listen to it.', ['True', 'False']),
        ('Some of my most vivid memories are called up by scents or sounds.', ['True', 'False']),
        ('Certain pieces of music remind me of pictures or moving patterns of color.', ['True', 'False']),
        ('I often know what someone is going to say before he/she/they says it.', ['True', 'False']),
        ("I often have 'physical memories'; for example, after I've been swimming, I may feel as if I'm in the water.", ['True', 'False']),
        ('The sound of a voice can be so fascinating to me that I can just go on listening to it.', ['True', 'False']),
        ('At times I somehow feel the presence of someone who is not physically there.', ['True', 'False']),
        ('Sometimes thoughts and images come to me without the slightest effort on my part.', ['True', 'False']),
        ('I find that different odors have different colors.', ['True', 'False']),
        ('I can be deeply moved by a sunset.', ['True', 'False']),
    ]
    
    intro = telleganScaleIntro
    return _run_questionnaire(win, subject_number, 'tellegen', questions, intro_text=intro)


def _vhq(subject_number: str, win: pg.Surface) -> list[str]:
    """Run the Voice Hearing Questionnaire (14 True/False questions)."""
    questions = [
        ("Sometimes I've thought I heard people say my name — like in a store when I walk past people I don't know — but I know they didn't really say my name, so I just go on.", ['True', 'False']),
        ("Sometimes when I'm just about to fall asleep, I hear my name as if spoken aloud.", ['True', 'False']),
        ('When I wake up in the morning but stay in bed for a few minutes, sometimes I hear my mother\'s voice when she\'s not there — like now when I\'m living in the dorm. I hear her saying things like "Come on and get up" or "Don\'t be late for school." I\'m used to it, and it doesn\'t bother me.', ['True', 'False']),
        ("I hear a voice that's kind of garbled — I can't really tell what it says — sometimes just as I go to sleep.", ['True', 'False']),
        ("I've had experiences of hearing something just as I'm going to sleep or waking up.", ['True', 'False']),
        ("When I was little, I had an imaginary playmate. I remember really thinking I heard her voice when we talked.", ['True', 'False']),
        ("When I had an imaginary playmate, I could actually hear their voice aloud. If you do not have an imaginary playmate, then respond 'False'.", ['True', 'False']),
        ("Every now and then — not very often — I think I hear my name on the radio.", ['True', 'False']),
        ('Sometimes when I\'m in the house all alone, I hear a voice call my name. It was scary at first, but now it isn\'t. It\'s just once — like "Sally!" — kind of quick, like somebody\'s calling me. I guess I know it\'s really me, but it still sounds like a real voice.', ['True', 'False']),
        ("Last summer, while hanging up clothes in the backyard, I suddenly heard my husband call my name from inside the house. It sounded loud and clear, like something was wrong — but he was outside and hadn't called at all.", ['True', 'False']),
        ("I've heard the doorbell or the phone ring when it didn't.", ['True', 'False']),
        ("I hear my thoughts aloud.", ['True', 'False']),
        ("I've heard God's voice — not just in my heart, but as a real voice.", ['True', 'False']),
        ('When I\'m driving in my car — particularly when I\'m tired or worried — I hear my own voice from the backseat. It sounds soothing, like "It\'ll be all right" or "Just calm down."', ['True', 'False']),
    ]
    
    intro = vhqIntro
    return _run_questionnaire(win, subject_number, 'vhq', questions, intro_text=intro)


def _launay_slade(subject_number: str, win: pg.Surface) -> list[str]:
    """Run the Launay-Slade Hallucination Scale (12 Likert questions)."""
    scale = ['1 - Not at all like me', '2', '3', '4', '5', '6', '7', '8 - Extremely like me']
    
    questions = [
        ('Sometimes a passing thought will seem so real that it frightens me.', scale),
        ('Sometimes my thoughts seem as real as actual events in my life.', scale),
        ('No matter how much I try to concentrate on my work unrelated thoughts always creep into my mind.', scale),
        ("In the past I have had the experience of hearing a person's voice and then found that there was no one there.", scale),
        ('The sounds I hear in my daydreams are generally clear and distinct.', scale),
        ('The people in my daydreams seem so true to life that I sometimes think they are.', scale),
        ('In my daydreams I can hear the sound of a tune almost as clearly as if I were actually listening to it.', scale),
        ('I often hear a voice speaking my thoughts aloud.', scale),
        ('I have never been troubled by hearing voices in my head.', scale),
        ("On occasions I have seen a person's face in front of me when no one was in fact there.", scale),
        ('I have never heard the voice of the Devil.', scale),
        ("In the past I have heard the voice of God speaking to me.", scale),
    ]
    
    intro = launeyScaleIntro
    return _run_questionnaire(win, subject_number, 'launay_slade', questions, intro_text=intro, extract_numeric=True)


def _dissociative_experiences(subject_number: str, win: pg.Surface) -> list[str]:
    """Run the Dissociative Experiences Scale (28 questions)."""
    scale = ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']
    
    questions = [
        ("Some people have the experience of driving a car and suddenly realizing that they don't remember what has happened during all or part of the trip. Select a box to show what percentage of the time this happens to you.", scale),
        ('Some people find that sometimes they are listening to someone talk and they suddenly realize that they did not hear all or part of what was said. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people have the experience of finding themselves in a place and having no idea how they got there. Select a box to show what percentage of the time this happens to you.', scale),
        ("Some people have the experience of finding themselves dressed in clothes that they don't remember putting on. Select a box to show what percentage of the time this happens to you.", scale),
        ('Some people have the experience of finding new things among their belongings that they do not remember buying. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people sometimes find that they are approached by people that they do not know who call them by another name or insist that they have met them before. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people sometimes have the experience of feeling as though they are standing next to themselves or watching themselves do something as if they were looking at another person. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people are told that they sometimes do not recognize friends or family members. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people find that they have no memory for some important events in their lives (for example, a wedding or graduation). Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people have the experience of being accused of lying when they do not think that they have lied. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people have the experience of looking in a mirror and not recognizing themselves. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people sometimes have the experience of feeling that other people, objects, and the world around them are not real. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people sometimes have the experience of feeling that their body does not seem to belong to them. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people have the experience of sometimes remembering a past event so vividly that they feel as if they were reliving that event. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people have the experience of not being sure whether things that they remember happening really did happen or whether they just dreamed them. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people have the experience of being in a familiar place but finding it strange and unfamiliar. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people find that when they are watching television or a movie they become so absorbed in the story that they are unaware of other events happening around them. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people sometimes find that they become so involved in a fantasy or daydream that it feels as though it were really happening to them. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people find that they sometimes are able to ignore pain. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people find that they sometimes sit staring off into space, thinking of nothing, and are not aware of the passage of time. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people sometimes find that when they are alone they talk out loud to themselves. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people find that in one situation they may act so differently compared with another situation that they feel almost as if they were two different people. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people sometimes find that in certain situations they are able to do things with amazing ease and spontaneity that would usually be difficult for them (for example, sports, work, social situations, etc.). Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people sometimes find that they cannot remember whether they have done something or have just thought about doing that thing (for example, not knowing whether they have just mailed a letter or have just thought about mailing it). Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people find evidence that they have done things that they do not remember doing. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people sometimes find writings, drawings, or notes among their belongings that they must have done but cannot remember doing. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people sometimes find that they hear voices inside their head that tell them to do things or comment on things that they are doing. Select a box to show what percentage of the time this happens to you.', scale),
        ('Some people sometimes feel as if they are looking at the world through a fog so that people and objects appear far away or unclear. Select a box to show what percentage of the time this happens to you.', scale),
    ]
    
    intro = dissociativeExperiencesIntro
    return _run_questionnaire(win, subject_number, 'dissociative_experiences', questions, intro_text=intro, extract_numeric=True)


def _flow_state_scale(subject_number: str, win: pg.Surface) -> list[str]:
    """Run the Flow State Scale (9 Likert questions)."""
    scale = ['1 - Strongly disagree', '2', '3 - Neither agree nor disagree', '4', '5 - Strongly agree']
    
    questions = [
        ('I feel I am competent enough to meet the demands of the situation', scale),
        ('I do things spontaneously and automatically without having to think', scale),
        ('I have a strong sense of what I want to do', scale),
        ('I have a good idea about how well I am doing while I am involved in the task/activity', scale),
        ('I am completely focused on the task at hand', scale),
        ('I have a feeling of total control over what I am doing', scale),
        ('I am not worried about what others may be thinking of me', scale),
        ('The way time passes seems to be different from normal', scale),
        ('The experience is extremely rewarding', scale),
    ]
    intro = flowStateIntro
    return _run_questionnaire(win, subject_number, 'flow_state_scale', questions, intro_text=intro, extract_numeric=True)


def _bais_v(subject_number: str, win: pg.Surface) -> list[str]:
    """Run BAIS-V (14 Likert questions)."""
    scale = ['1 - No Image Present At All', '2', '3', '4 - Fairly Vivid Image', '5', '6', '7 - Image as Vivid as Actual Sound']
    
    questions = [
        ('For this item, consider attending a choir rehearsal. Imagine hearing an all-children\'s choir singing the first verse of a song.', scale),
        ('For this item, consider being present at a jazz club. Imagine hearing a saxophone solo.', scale),
        ('For this item, consider listening to a rain storm. Imagine hearing gentle rain.', scale),
        ('For this item, consider driving in a car. Imagine hearing an upbeat rock song on the radio.', scale),
        ('For this item, consider ordering something over the phone. Imagine hearing the voice of an elderly clerk assisting you.', scale),
        ('For this item, consider seeing a live opera performance. Imagine hearing the voice of an opera singer in the middle of a verse.', scale),
        ('For this item, consider going to a dentist appointment. Imagine hearing the loud sound of the dentist\'s drill.', scale),
        ('For this item, consider the beginning of the song "Happy Birthday." Imagine hearing a trumpet beginning the piece.', scale),
        ('For this item, consider attending an orchestral performance of Beethoven\'s Fifth. Imagine the sound of the ensemble playing.', scale),
        ('For this item, consider attending a new tap-dance performance. Imagine the sound of tap-shoes on the stage.', scale),
        ('For this item, consider being at a live baseball game. Imagine the cheer of the crowd as a player hits the ball.', scale),
        ('For this item, consider a kindergarten class. Imagine hearing the voice of the teacher reading a story to the children.', scale),
        ('For this item, consider attending classes. Imagine hearing the slow-paced voice of your English teacher.', scale),
        ('For this item, consider being at the beach. Imagine the sound of the waves crashing against nearby rocks.', scale),
    ]
    
    intro = baisVIntro
    return _run_questionnaire(win, subject_number, 'bais_v', questions, intro_text=intro, extract_numeric=True)


def _bais_c(subject_number: str, win: pg.Surface) -> list[str]:
    """Run BAIS-C (14 Likert questions about changing auditory images)."""
    scale = ['1 - No Image Present At All', '2', '3', '4 - Could Change the Image but With Effort', '5', '6', '7 - Extremely Easy to Change the Image']
    
    questions = [
        ('For the first pair, consider attending a choir rehearsal.\n\na. The sound of an all-children\'s choir singing the first verse of a song.\nb. An all-adults\' choir now sings the second verse of the song.', scale),
        ('For the next pair, consider being present at a jazz club.\n\na. The sound of a saxophone solo.\nb. The saxophone is now accompanied by a piano.', scale),
        ('For the next pair, consider listening to a rain storm.\n\na. The sound of gentle rain.\nb. The gentle rain turns into a violent thunderstorm.', scale),
        ('For the next pair, consider driving in a car.\n\na. The sound of an upbeat rock song on the radio.\nb. The song is now masked by the sound of the car coming to a screeching halt.', scale),
        ('For the next pair, consider ordering something over the phone.\n\na. The voice of an elderly clerk assisting you.\nb. The elderly clerk leaves and the voice of a younger clerk is now on the line.', scale),
        ('For the next pair, consider seeing a live opera performance.\n\na. The voice of an opera singer in the middle of a verse.\nb. The opera singer now reaches the end of the piece and holds the final note.', scale),
        ('For the next pair, consider going to a dentist appointment.\n\na. The loud sound of the dentist\'s drill.\nb. The drill stops and you can now hear the soothing voice of the receptionist.', scale),
        ('For the next pair, consider the beginning of the song "Happy Birthday."\n\na. The sound of a trumpet beginning the piece.\nb. The trumpet stops and a violin continues the piece.', scale),
        ('For the next pair, consider attending an orchestral performance of Beethoven\'s Fifth.\n\na. The sound of the ensemble playing.\nb. The ensemble stops but the sound of a piano solo is present.', scale),
        ('For the next pair, consider attending a new tap-dance performance.\n\na. The sound of tap-shoes on the stage.\nb. The sound of the shoes speeds up and gets louder.', scale),
        ('For the next pair, consider being at a live baseball game.\n\na. The cheer of the crowd as a player hits the ball.\nb. Now the crowd boos as the fielder catches the ball.', scale),
        ('For the next pair, consider a kindergarten class.\n\na. The voice of the teacher reading a story to the children.\nb. The teacher stops reading for a minute to talk to another teacher.', scale),
        ('For the next pair, consider attending classes.\n\na. The slow-paced voice of your English teacher.\nb. The pace of the teacher\'s voice gets faster at the end of class.', scale),
        ('For the next pair, consider being at the beach.\n\na. The sound of the waves crashing against nearby rocks.\nb. The waves are now drowned out by the loud sound of a boat\'s horn out at sea.', scale),
    ]
    
    intro = baisCIntro
    return _run_questionnaire(win, subject_number, 'bais_c', questions, intro_text=intro, extract_numeric=True)


def stanford_sleepiness_scale(subject_number: str, win: pg.Surface) -> str:
    """Run Stanford Sleepiness Scale (single question)."""
    pg.mouse.set_visible(True)
    
    options = [
        '1 - Feeling active and vital; alert; wide awake.',
        '2 - Functioning at a high level, but not at peak; able to concentrate.',
        '3 - Relaxed; awake; not at full alertness; responsive.',
        '4 - A little foggy; not at peak; let down.',
        '5 - Fogginess; beginning to lose interest in remaining awake; slowed down.',
        '6 - Sleepiness; prefer to be lying down; fighting sleep; woozy.',
        '7 - Almost in reverie; sleep onset soon; lost struggle to remain awake'
    ]
    
    response = _run_single_question(
        win,
        'Please indicate your current level of sleepiness:',
        options,
        'sleepiness'
    )
    
    return response


# =============================================================================
# RECALL QUESTIONS (Text entry)
# =============================================================================

def _run_recall_questions(subject_number: str, win: pg.Surface) -> None:
    """Ask subject to recall the target word and sentence, save responses."""
    screen = Screen(win)
    
    # Event logging
    results_dir = os.path.join(_BASE_DIR, 'results', subject_number)
    screen_logger = ScreenEventLogger('recall_questions', results_dir, subject_number)
    
    # Question 1: Target word
    text_input_word = TextInput(
        screen,
        mode=InputMode.ALPHANUMERIC_SPACES,
        placeholder="Type your answer here...",
    )
    word_response = text_input_word.run(
        prompt="Please type the **word** that you were listening for during this experiment.\n\n**Response**"
    )
    if word_response:
        screen_logger.log_event('text_submitted', 'target_word')
    
    # Question 2: Target sentence
    text_input_sentence = TextInput(
        screen,
        mode=InputMode.ALPHANUMERIC_SPACES,
        placeholder="Type your answer here...",
    )
    sentence_response = text_input_sentence.run(
        prompt="Please type the **sentence** you listened to throughout this experiment.\n\n**Response**"
    )
    if sentence_response:
        screen_logger.log_event('text_submitted', 'target_sentence')
    
    # Save event log
    screen_logger.save()
    
    # Save responses
    os.makedirs(results_dir, exist_ok=True)
    
    filepath = os.path.join(results_dir, f'recall_responses_{subject_number}.csv')
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Subject Number', 'Target Word Response', 'Target Sentence Response'])
        writer.writerow([subject_number, word_response or '', sentence_response or ''])


# =============================================================================
# PUBLIC API
# =============================================================================

def run_questionnaires(subject_number: str, win: pg.Surface) -> None:
    """Run all questionnaires for the subject."""
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    # Event logging
    results_dir = os.path.join(_BASE_DIR, 'results', subject_number)
    intro_logger = ScreenEventLogger('questionnaires_intro', results_dir, subject_number)
    
    # Show intro message
    pg.mouse.set_visible(False)
    style = TextStyle(
        font_size=screen.scaled_font_size(20),
        color=Colors.BLACK,
        align=TextAlign.LEFT,
    )
    
    waiting = True
    while waiting:
        screen.fill()
        text_renderer.draw_text_block(
            questionnairesIntro,
            rel_x=0.05,
            rel_y=0.05,
            max_width=screen.abs_x(0.9),
            style=style,
        )
        screen.update()
        
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()
                elif event.key == pg.K_SPACE:
                    intro_logger.log_event('key_press', 'space')
                    intro_logger.save()
                    waiting = False
    
    # Run all questionnaires
    _tellegen(subject_number, win)
    _vhq(subject_number, win)
    _flow_state_scale(subject_number, win)
    _launay_slade(subject_number, win)
    _dissociative_experiences(subject_number, win)
    _bais_v(subject_number, win)
    _bais_c(subject_number, win)
    
    # Text response screens for recall
    _run_recall_questions(subject_number, win)
    
    pg.mouse.set_visible(True)


def save_sleepiness_data(
    subject_number: str,
    save_folder: str,
    sleepiness_responses: list,
) -> None:
    """Save sleepiness scale responses to a CSV file."""
    filepath = os.path.join(save_folder, f'sleepiness_{subject_number}.csv')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(filepath, mode='w', newline='') as f:
        writer = csv.writer(f)
        
        # Build header based on response structure
        header = ['Subject Number', 'Timestamp']
        for i, resp in enumerate(sleepiness_responses):
            if isinstance(resp, dict):
                header.append(f"Block{resp.get('block', i)}_{resp.get('timing', 'unknown')}")
            else:
                header.append(f'Rating_{i+1}')
        
        writer.writerow(header)
        
        # Extract values
        values = [subject_number, timestamp]
        for resp in sleepiness_responses:
            if isinstance(resp, dict):
                values.append(resp.get('response', ''))
            else:
                values.append(resp)
        
        writer.writerow(values)


def run_stanford_sleepiness(subject_number: str, win: pg.Surface) -> str:
    """Run the Stanford Sleepiness Scale and return the response."""
    return stanford_sleepiness_scale(subject_number, win)
