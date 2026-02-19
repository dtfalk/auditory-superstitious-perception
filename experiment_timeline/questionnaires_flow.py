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
    tellegenScaleIntro, launeyScaleIntro, dissociativeExperiencesIntro,
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
    elif questionnaire_name in ('sleepiness', 'stanford_sleepiness'):
        # Stanford Sleepiness uses dynamic spacing based on wrapped lines
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


def _count_wrapped_lines(text: str, font: pg.font.Font, max_width: int) -> int:
    """Count how many lines text will wrap to given max_width."""
    if max_width <= 0:
        return 1
    words = text.split()
    if not words:
        return 1
    lines = 1
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        test_surf = font.render(test_line, True, (0, 0, 0))
        if test_surf.get_width() <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines += 1
            current_line = [word]
    return lines


def _precompute_option_slots(
    questionnaire_name: str,
    win: pg.Surface,
    y_pos_question_fixed: int,
    max_options: int,
    option_texts: list[str] | None = None,
) -> list[dict]:
    """Create stable checkbox positions based on worst-case option count.

    The slots are reused for every question so options never shift.
    If option_texts is provided, uses dynamic spacing based on wrapped line counts.
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

    x_left = int(0.05 * current_w)
    x_right = int(0.05 * current_w + 0.45 * current_w)
    
    # Calculate max text width for wrapping
    # Leave room for checkbox (button_size + 10px gap) and padding
    max_text_width = int(0.85 * current_w) - button_size - 20
    
    # If option_texts provided, use dynamic spacing based on actual wrapped lines
    if option_texts:
        pg.font.init()
        font = pg.font.SysFont("times new roman", font_size)
        line_height = int(font_size * 1.15)
        base_row_height = int(scalar * font_size)
        
        slots: list[dict] = []
        y_current = y_start
        
        for idx, text in enumerate(option_texts):
            num_lines = _count_wrapped_lines(text, font, max_text_width)
            # Height needed: base height + extra for additional wrapped lines
            row_height = base_row_height + (num_lines - 1) * line_height
            
            slots.append({
                'x': x_left,
                'y': y_current,
                'button_size': button_size,
                'font_size': font_size,
                'max_text_width': max_text_width,
            })
            y_current += row_height
        
        return slots

    # Original fixed-spacing logic for questionnaires without option_texts
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

    # Center columns when there are 2
    if n_cols == 2:
        col_width = int(0.45 * current_w)
        total_width = 2 * col_width
        left_margin = (current_w - total_width) // 2
        x_left = left_margin
        x_right = left_margin + col_width
        max_text_width = col_width - button_size - 30
    
    left_count = max_options if n_cols == 1 else math.ceil(max_options / 2)

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
    
    # Log that this question screen is being presented
    if screen_logger:
        screen_logger.log_event('screen_presented', f'Q{question_index + 1}')

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
        # Fallback: compute per-question with dynamic spacing based on actual text
        screen.fill()
        y_after_question = text_renderer.draw_text_block(
            question_text, rel_x=0.05, rel_y=0.05,
            max_width=screen.abs_x(0.9), style=question_style,
        )
        slots = _precompute_option_slots(questionnaire_name, win, y_after_question, n_options, option_texts=options)
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
        header = ["subject_number"] + [f'Q{i+1}' for i in range(len(questions))]
        writer.writerow(header)
        
        # Row 1: numerical values
        if extract_numeric:
            numeric_values = [''.join(c for c in r if c.isdigit()) for r in responses]
        elif questionnaire_name == 'vhq':
            # VHQ uses Yes/No scale - convert to 1/0
            numeric_values = ['1' if r == 'Yes' else '0' for r in responses]
        else:
            numeric_values = responses
        writer.writerow([subject_number] + numeric_values)
        
        # Row 2: text labels (replace commas with semicolons to preserve CSV structure)
        text_labels = [r.replace(',', ';') for r in responses]
        writer.writerow([subject_number] + text_labels)
    
    return responses


# =============================================================================
# INDIVIDUAL QUESTIONNAIRES
# =============================================================================
def _tellegen(subject_number: str, win: pg.Surface) -> list[str]:
    """Run the Tellegen Absorption Scale (4-point Likert version)."""

    scale = [
        '0 - Never',
        '1 - Rarely',
        '2 - Often',
        '3 - Always'
    ]

    questions = [
        ('Sometimes I feel and experience things as I did when I was a child.', scale),
        ('I can be greatly moved by eloquent or poetic language.', scale),
        ('While watching a movie, a TV show, or a play, I may sometimes become so involved that I forget about myself and my surroundings and experience the story as if it were real and as if I were taking part in it.', scale),
        ('If I stare at a picture and then look away from it, I can sometimes "see" an image of the picture, almost as if I were still looking at it.', scale),
        ('Sometimes I feel as if my mind could envelop the whole earth.', scale),
        ('I like to watch cloud shapes in the sky.', scale),
        ('If I wish, I can imagine (or daydream) some things so vividly that they hold my attention as a good movie or a story does.', scale),
        ('I think I really know what some people mean when they talk about mystical experiences.', scale),
        ('I sometimes "step outside" my usual self and experience an entirely different state of being.', scale),
        ('Textures such as wool, sand, wood sometimes remind me of colors or music.', scale),
        ('Sometimes I experience things as if they were doubly real.', scale),
        ("When I listen to music, I can get so caught up in it that I don't notice anything else.", scale),
        ('If I wish, I can imagine that my whole body is so heavy that I could not move it if I wanted to.', scale),
        ('I can often somehow sense the presence of another person before I actually see or hear him/her.', scale),
        ('The crackle and flames of a woodfire stimulate my imagination.', scale),
        ('It is sometimes possible for me to be completely immersed in nature or art and to feel as if my whole state of consciousness has somehow been temporarily altered.', scale),
        ('Different colors have distinctive and special meanings to me.', scale),
        ('I am able to wander off into my own thought while doing a routine task and actually forget that I am doing the task, and then find a few minutes later that I have completed it.', scale),
        ('I can sometimes recollect certain past experiences in my life with such clarity and vividness that it is like living them again or almost so.', scale),
        ('Things that might seem meaningless to others often make sense to me.', scale),
        ('While acting in a play, I think I would really feel the emotions of the character and "become" him/her for the time being, forgetting both myself and the audience.', scale),
        ('My thoughts often do not occur as words but as visual images.', scale),
        ('I often take delight in small things (like the five pointed star shape that appears when you cut an apple across the core or the colors in soap bubbles).', scale),
        ('When listening to organ music or other powerful music I sometimes feel as if I am being lifted into the air.', scale),
        ('Sometimes I can change noise into music by the way I listen to it.', scale),
        ('Some of my most vivid memories are called up by scents and smells.', scale),
        ('Certain pieces of music remind me of pictures or moving patterns of color.', scale),
        ('I often know what someone is going to say before he or she says it.', scale),
        ('I often have "physical memories"; for example, after I have been swimming I may still feel as if I am in the water.', scale),
        ('The sound of a voice can be so fascinating to me that I can just go on listening to it.', scale),
        ('At times I somehow feel the presence of someone who is not physically there.', scale),
        ('Sometimes thoughts and images come to me without the slightest effort on my part.', scale),
        ('I find that different odors have different colors.', scale),
        ('I can be deeply moved by a sunset.', scale),
    ]

    return _run_questionnaire(win, subject_number, 'tellegen', questions, intro_text=tellegenScaleIntro, extract_numeric=True)




def _vhq(subject_number: str, win: pg.Surface) -> list[str]:
    """Run the Hearing Voices Questionnaire (Posey & Losch, 1983)."""

    scale = ['Yes', 'No']

    questions = [
        ("Sometimes I have thought I heard people say my name... like in a store when you walk past some people you don't know... but I know they didn't really say my name so I just go on.\n\nHas something like this ever happened to you?", scale),
        ("Sometimes when I am just about to fall asleep, I hear my name as if spoken aloud.\n\nHappened to you?", scale),
        ("When I wake up in the morning... but stay in bed for a few minutes, sometimes I hear my mother's voice... when she's not there. Like now when I'm living in the dorm. What I hear is her voice saying stuff like, 'Now come on and get up' or 'Don't be late for school.' I'm used to it and it doesn't bother me.\n\nHas a similar experience happened to you?", scale),
        ("I hear a voice that is kind of garbled... can't really tell what it says... sometimes just as I go to sleep.\n\nHappened to you?", scale),
        ("I've had experiences of hearing something just when going asleep or waking up.\n\nHave you had any experience with hearing something just when going asleep or waking up?", scale),
        ("When I was little, I had an imaginary playmate. I remember that I really thought I heard her voice when we talked. That went away... hearing her voice... but for awhile it was just like a real voice.\n\nDid you have an imaginary playmate and hear his/her voice aloud?", scale),
        ("Every now and then — not real often — I think I hear my name on the radio.\n\nHappened to you?", scale),
        ("Sometimes when I'm in the house all alone, I hear a voice call my name. No, it really isn't scary. It was at first, but not now... it's just once... like 'Sally'... kind of quick and like somebody's calling me. I guess I kind of know that it really isn't somebody and it's really me... but it does sound like a real voice.\n\nHappened to you?", scale),
        ("Last summer I was hanging-up clothes in the backyard. Suddenly I heard my husband call my name from inside the house. He sounded like something was wrong and was loud and clear. I ran in... but he was out in the garage and hadn't called at all. Obviously I guess I made it up... but it sounded like a real voice and it was my husband's.\n\nThis or something similar happen to you?", scale),
        ("I've heard the doorbell or the phone ring when it didn't.\n\nHappen to you?", scale),
        ("I hear my thoughts aloud.\n\nHappen to you?", scale),
        ("I have heard God's voice... not that he made me know in my heart... but as a real voice.\n\nHappen to you?", scale),
        ("I drive a lot at night. My job has a lot of travel to it. Sometimes late at night, when I'm tired, I hear sounds in the backseat like people talking... but I can't tell what they say... just a word here and there. When this first started happening... when I first started driving at night so much... four or five years ago... it scared the hell out of me. But now I'm used to it. I think I do it because I'm tired and by myself.\n\nAnything similar happen to you?", scale),
        ("Almost every morning while I do my housework, I have a pleasant conversation with my dead grandmother. I talk to her and quite regularly hear her voice actually aloud.\n\nAnything similar happen to you?", scale),
    ]

    return _run_questionnaire(win, subject_number, 'vhq', questions, intro_text=vhqIntro)


def _launay_slade(subject_number: str, win: pg.Surface) -> list[str]:
    """Run the Launay-Slade Hallucination Scale – Extended (16 Likert questions)."""
    scale = ['0 - Certainly does not apply to me', 
             '1 - Possibly does not apply to me', 
             '2 - Unsure',
             '3 - Possibly applies to me',
             '4 - Certainly applies to me'
            ]
    
    questions = [
        ('Sometimes a passing thought will seem so real that it frightens me.', scale),
        ('Sometimes my thoughts seem as real as actual events in my life.', scale),
        ('No matter how much I try to concentrate on my work unrelated thoughts always creep into my mind.', scale),
        ("In the past I have had the experience of hearing a person's voice and then found that there was no one there.", scale),
        ('The sounds I hear in my daydreams are generally clear and distinct.', scale),
        ('The people in my daydreams seem so true to life that I sometimes think they are.', scale),
        ('In my daydreams I can hear the sound of a tune almost as clearly as if I were actually listening to it.', scale),
        ('I often hear a voice speaking my thoughts aloud.', scale),
        ('I have been troubled by hearing voices in my head.', scale),
        ("On occasions I have seen a person's face in front of me when no-one was in fact there.", scale),
        ('Sometimes, immediately prior to falling asleep or upon awakening, I have had the experience of having seen, felt or heard something or someone that wasn’t there, or I had the feeling of being touched even though no one was there.', scale),
        ('Sometimes, immediately prior to falling asleep or upon awakening, I have felt that I was floating or falling, or that I was leaving my body temporarily.', scale),
        ('On certain occasions I have felt the presence of someone close who had passed away.', scale),
        ('In the past, I have smelt a particular odour even though there was nothing there.', scale),
        ("I have had the feeling of touching something or being touched and then found that nothing or no one was there.", scale),
        ("Sometimes, I have seen objects or animals even though there was nothing there.", scale),
    ]
    
    intro = launeyScaleIntro
    return _run_questionnaire(win, subject_number, 'launay_slade', questions, intro_text=intro, extract_numeric=True)


def _dissociative_experiences(subject_number: str, win: pg.Surface) -> list[str]:
    """Run the Dissociative Experiences Scale (28 questions)."""
    scale = ['0% (Never)', '10', '20', '30', '40', '50', '60', '70', '80', '90', '100% (Always)']
    
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
    """Run the Short Flow State Scale (S FSS-2)."""

    scale = [
        '1 - Strongly Disagree',
        '2 - Disagree',
        '3 - Neither Agree nor Disagree',
        '4 - Agree',
        '5 - Strongly Agree'
    ]

    questions = [
        ('I felt I was competent enough to meet the demands of the situation.', scale),
        ('I did things spontaneously and automatically without having to think.', scale),
        ('I had a strong sense of what I wanted to do.', scale),
        ('I had a good idea about how well I was doing while I was involved in the task/activity.', scale),
        ('I was completely focused on the task at hand.', scale),
        ('I had a feeling of total control over what I was doing.', scale),
        ('I was not worried about what others may have been thinking of me.', scale),
        ('The way time passed seemed to be different from normal.', scale),
        ('I found the experience extremely rewarding.', scale),
    ]

    intro = flowStateIntro

    return _run_questionnaire(
        win,
        subject_number,
        'flow_state_scale',
        questions,
        intro_text=intro,
        extract_numeric=True
    )



def _bais_v(subject_number: str, win: pg.Surface) -> list[str]:
    """Run BAIS-V (Bucknell Auditory Imagery Scale – Vividness)."""

    scale = [
        '1 - No Image Present at All',
        '2',
        '3',
        '4 - Fairly Vivid',
        '5',
        '6',
        '7 - As Vivid As the Actual Sound'
    ]

    questions = [
        ('For this item, consider the beginning of the song "Happy Birthday." Imagine hearing a trumpet beginning the piece.', scale),
        ('For this item, consider ordering something over the phone. Imagine hearing the voice of an elderly clerk assisting you.', scale),
        ('For this item, consider being at the beach. Imagine the sound of the waves crashing against nearby rocks.', scale),
        ('For this item, consider going to a dentist appointment. Imagine hearing the loud sound of the dentist\'s drill.', scale),
        ('For this item, consider being present at a jazz club. Imagine hearing a saxophone solo.', scale),
        ('For this item, consider being at a live baseball game. Imagine the cheer of the crowd as a player hits the ball.', scale),
        ('For this item, consider attending a choir rehearsal. Imagine hearing an all-children\'s choir singing the first verse of a song.', scale),
        ('For this item, consider attending an orchestral performance of Beethoven\'s Fifth. Imagine the sound of the ensemble playing.', scale),
        ('For this item, consider listening to a rain storm. Imagine hearing gentle rain.', scale),
        ('For this item, consider attending classes. Imagine hearing the slow-paced voice of your English teacher.', scale),
        ('For this item, consider seeing a live opera performance. Imagine hearing the voice of an opera singer in the middle of a verse.', scale),
        ('For this item, consider attending a new tap-dance performance. Imagine the sound of tap-shoes on the stage.', scale),
        ('For this item, consider a kindergarten class. Imagine hearing the voice of the teacher reading a story to the children.', scale),
        ('For this item, consider driving in a car. Imagine hearing an upbeat rock song on the radio.', scale),
    ]

    intro = baisVIntro

    return _run_questionnaire(win, subject_number, 'bais_v', questions, intro_text=intro, extract_numeric=True)



def _bais_c(subject_number: str, win: pg.Surface) -> list[str]:
    """Run BAIS-C (Bucknell Auditory Imagery Scale – Control)."""

    scale = [
        '1 - No Image Present at All',
        '2',
        '3',
        '4 - Could Change the Image but With Effort',
        '5',
        '6',
        '7 - Extremely Easy to Change the Image'
    ]

    questions = [
        ('For this pair, consider the beginning of the song "Happy Birthday."\n\n'
         'a. The sound of a trumpet beginning the piece.\n'
         'b. The trumpet stops and a violin continues the piece.',
         scale),

        ('For this pair, consider ordering something over the phone.\n\n'
         'a. The voice of an elderly clerk assisting you.\n'
         'b. The elderly clerk leaves and the voice of a younger clerk is now on the line.',
         scale),

        ('For this pair, consider being at the beach.\n\n'
         'a. The sound of the waves crashing against nearby rocks.\n'
         'b. The waves are now drowned out by the loud sound of a boat\'s horn out at sea.',
         scale),

        ('For this pair, consider going to a dentist appointment.\n\n'
         'a. The loud sound of the dentist\'s drill.\n'
         'b. The drill stops and you can now hear the soothing voice of the receptionist.',
         scale),

        ('For this pair, consider being present at a jazz club.\n\n'
         'a. The sound of a saxophone solo.\n'
         'b. The saxophone is now accompanied by a piano.',
         scale),

        ('For this pair, consider being at a live baseball game.\n\n'
         'a. The cheer of the crowd as a player hits the ball.\n'
         'b. Now the crowd boos as the fielder catches the ball.',
         scale),

        ('For this pair, consider attending a choir rehearsal.\n\n'
         'a. The sound of an all-children\'s choir singing the first verse of a song.\n'
         'b. An all-adults\' choir now sings the second verse of the song.',
         scale),

        ('For this pair, consider attending an orchestral performance of Beethoven\'s Fifth.\n\n'
         'a. The sound of the ensemble playing.\n'
         'b. The ensemble stops but the sound of a piano solo is present.',
         scale),

        ('For this pair, consider listening to a rain storm.\n\n'
         'a. The sound of gentle rain.\n'
         'b. The gentle rain turns into a violent thunderstorm.',
         scale),

        ('For this pair, consider attending classes.\n\n'
         'a. The slow-paced voice of your English teacher.\n'
         'b. The pace of the teacher\'s voice gets faster at the end of class.',
         scale),

        ('For this pair, consider seeing a live opera performance.\n\n'
         'a. The voice of an opera singer in the middle of a verse.\n'
         'b. The opera singer now reaches the end of the piece and holds the final note.',
         scale),

        ('For this pair, consider attending a new tap-dance performance.\n\n'
         'a. The sound of tap-shoes on the stage.\n'
         'b. The sound of the shoes speeds up and gets louder.',
         scale),

        ('For this pair, consider a kindergarten class.\n\n'
         'a. The voice of the teacher reading a story to the children.\n'
         'b. The teacher stops reading for a minute to talk to another teacher.',
         scale),

        ('For this pair, consider driving in a car.\n\n'
         'a. The sound of an upbeat rock song on the radio.\n'
         'b. The song is now masked by the sound of the car coming to a screeching halt.',
         scale),
    ]

    intro = baisCIntro

    return _run_questionnaire(win, subject_number, 'bais_c', questions, intro_text=intro, extract_numeric=True)



def stanford_sleepiness_scale(subject_number: str, win: pg.Surface) -> str:
    """Run Stanford Sleepiness Scale (SSS)."""

    pg.mouse.set_visible(True)

    options = [
        '1 - Feeling active, vital, alert, or wide awake',
        '2 - Functioning at high levels, but not at peak; able to concentrate',
        '3 - Awake, but relaxed; responsive but not fully alert',
        '4 - Somewhat foggy, let down',
        '5 - Foggy; losing interest in remaining awake; slowed down',
        '6 - Sleepy, woozy, fighting sleep; prefer to lie down',
        '7 - No longer fighting sleep, sleep onset soon; having dream-like thoughts'
    ]

    response = _run_single_question(
        win,
        'Please select the statement that best describes your current level of sleepiness:',
        options,
        'stanford_sleepiness'
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
    
    # Question 3: Listening experience
    text_input_experience = TextInput(
        screen,
        mode=InputMode.ALPHANUMERIC_SPACES,
        placeholder="Type your answer here...",
    )
    experience_response = text_input_experience.run(
        prompt=(
            "Do you have any special **listening experience** or training "
            "that might be relevant to this experiment?\n\n"
            "For example: playing a musical instrument, audio engineering, "
            "vocal training, working in a listening-intensive profession, "
            "or any other relevant auditory experience.\n\n"
            "If not, simply type **none**.\n\n**Response**"
        )
    )
    if experience_response:
        screen_logger.log_event('text_submitted', 'listening_experience')
    
    # Question 4: Technical issues
    text_input_technical = TextInput(
        screen,
        mode=InputMode.ALPHANUMERIC_SPACES,
        placeholder="Type your answer here...",
    )
    technical_response = text_input_technical.run(
        prompt=(
            "Did you experience any **technical issues** during this experiment "
            "that may have affected your performance or attention? "
            "This could include audio glitches, software errors, "
            "equipment malfunctions, environmental disturbances, "
            "or any other factors that interfered with your ability to complete the task.\n\n"
            "If not, simply type **none**. If so, please describe the nature of the disturbance, how often they occurred, and the degree to which it affected your ability to engage with the experiment.\n\n**Response**"
        )
    )
    if technical_response:
        screen_logger.log_event('text_submitted', 'technical_issues')
    
    # Save event log
    screen_logger.save()
    
    # Save responses as separate .txt files
    os.makedirs(results_dir, exist_ok=True)
    
    # Target word response
    word_path = os.path.join(results_dir, f'recall_target_word_{subject_number}.txt')
    with open(word_path, 'w') as f:
        f.write(word_response or '')
    
    # Target sentence response
    sentence_path = os.path.join(results_dir, f'recall_target_sentence_{subject_number}.txt')
    with open(sentence_path, 'w') as f:
        f.write(sentence_response or '')
    
    # Save listening experience as separate .txt
    exp_path = os.path.join(results_dir, f'listening_experience_{subject_number}.txt')
    with open(exp_path, 'w') as f:
        f.write(experience_response or '')
    
    # Save technical issues as separate .txt
    tech_path = os.path.join(results_dir, f'technical_issues_{subject_number}.txt')
    with open(tech_path, 'w') as f:
        f.write(technical_response or '')


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
    _flow_state_scale(subject_number, win)
    _tellegen(subject_number, win)
    _vhq(subject_number, win)
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
    """Save sleepiness scale responses to a CSV file.
    
    Format: One row per sleepiness measurement with columns:
    subject_number, block_index, block_scheme, pre_or_post, time, response, response_text
    """
    # Stanford sleepiness options for mapping response number to text
    sleepiness_options = {
        '1': '1 - Feeling active; vital; alert; or wide awake',
        '2': '2 - Functioning at high levels; but not at peak; able to concentrate',
        '3': '3 - Awake; but relaxed; responsive but not fully alert',
        '4': '4 - Somewhat foggy; let down',
        '5': '5 - Foggy; losing interest in remaining awake; slowed down',
        '6': '6 - Sleepy; woozy; fighting sleep; prefer to lie down',
        '7': '7 - No longer fighting sleep; sleep onset soon; having dream-like thoughts'
    }
    
    filepath = os.path.join(save_folder, f'stanford_sleepiness_{subject_number}.csv')
    
    with open(filepath, mode='w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        header = ['subject_number', 'block_index', 'block_scheme', 'pre_or_post', 'time', 'response', 'response_text']
        writer.writerow(header)
        
        # One row per response
        for resp in sleepiness_responses:
            if isinstance(resp, dict):
                response_val = resp.get('response', '')
                # Extract just the number from the response
                response_num = ''.join(c for c in str(response_val) if c.isdigit())[:1] or response_val
                # Get full text (with commas replaced by semicolons)
                response_text = sleepiness_options.get(response_num, str(response_val).replace(',', ';'))
                
                row = [
                    subject_number,
                    resp.get('block_index', ''),
                    resp.get('block_scheme', ''),
                    resp.get('timing', ''),
                    resp.get('time', ''),
                    response_num,
                    response_text
                ]
                writer.writerow(row)


def run_stanford_sleepiness(subject_number: str, win: pg.Surface) -> str:
    """Run the Stanford Sleepiness Scale and return the response."""
    return stanford_sleepiness_scale(subject_number, win)
