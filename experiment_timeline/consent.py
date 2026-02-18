"""
Consent Subtimeline
===================
Handles the consent flow including:
- Subject info collection
- Study information screens
- Consent agreement

Uses displayEngine for all rendering - no dependency on helperFunctions.py
"""

import os
import sys
import pygame as pg

# Add parent directory for imports
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE_DIR)
sys.path.insert(0, os.path.join(_BASE_DIR, 'experiment_helpers'))
sys.path.insert(0, os.path.join(_BASE_DIR, 'utils'))

from utils.displayEngine import (
    Screen, TextRenderer, TextInput, Button, ButtonStyle,
    Colors, TextStyle, TextAlign, InputMode,
)
from utils.eventLogger import ScreenEventLogger
from experiment_helpers.text_blocks.consentTextBlocks import (
    studyInfoText, incentivesText, risksAndBenefitsText, 
    confidentialityText, contactsAndQuestionsText, nonConsentText
)


# =============================================================================
# SUBJECT INFO COLLECTION
# =============================================================================

def _get_subject_input(
    win: pg.Surface,
    prompt: str,
    mode: InputMode = InputMode.ALPHANUMERIC_SPACES,
    placeholder: str = "",
) -> str:
    """
    Collect text input from user using displayEngine.TextInput.
    
    Args:
        win: pygame surface
        prompt: Text to display above input
        mode: Input mode restrictions
        placeholder: Placeholder text
    
    Returns:
        User's input string
    """
    screen = Screen(win)
    text_input = TextInput(
        screen,
        mode=mode,
        allow_spaces=(mode == InputMode.ALPHANUMERIC_SPACES),
        allow_shift_symbols=(mode == InputMode.FULL_ASCII),
        placeholder=placeholder,
    )
    
    result = text_input.run(prompt=prompt)
    return result if result else ""


def collect_subject_info(win: pg.Surface) -> dict:
    """
    Collect subject information (experimenter name, subject number, name, email).
    
    Returns:
        Dictionary containing subject info
    """
    base_prompt = "Please enter the requested information. Press Enter to continue, ESC to exit.\n\n"
    
    experimenter_name = _get_subject_input(
        win,
        prompt=base_prompt + "**Experimenter Name**",
        mode=InputMode.ALPHANUMERIC_SPACES,
        placeholder="Enter experimenter name..."
    )
    
    subject_number = _get_subject_input(
        win,
        prompt=base_prompt + "**Subject Number**",
        mode=InputMode.NUMBERS_ONLY,
        placeholder="Enter subject number..."
    )
    
    subject_name = _get_subject_input(
        win,
        prompt=base_prompt + "**Subject Name**",
        mode=InputMode.ALPHANUMERIC_SPACES,
        placeholder="Enter subject name..."
    )
    
    subject_email = _get_subject_input(
        win,
        prompt=base_prompt + "**Subject Email**",
        mode=InputMode.EMAIL,
        placeholder="Enter email address..."
    )

    return {
        'experimenter_name': experimenter_name,
        'subject_number': subject_number,
        'subject_name': subject_name,
        'subject_email': subject_email,
    }


def create_save_folder(subject_number: str) -> tuple[str, str]:
    """
    Create and return the save folder path for the subject.
    Handles duplicate subject numbers by appending '0'.
    
    Returns:
        Tuple of (final subject number, save folder path)
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    save_folder = os.path.join(base_dir, 'results', subject_number)

    while os.path.exists(save_folder):
        subject_number = subject_number + '0'
        save_folder = os.path.join(base_dir, 'results', subject_number)

    os.makedirs(save_folder, exist_ok=True)
    return subject_number, save_folder


# =============================================================================
# CONSENT SCREEN PAGES
# =============================================================================

def _show_text_page(
    win: pg.Surface,
    text: str,
    allow_back: bool = False,
) -> str:
    """
    Display a page of text and wait for navigation input.
    
    Args:
        win: pygame surface
        text: Text content to display
        allow_back: Whether to allow left arrow (back)
    
    Returns:
        "next", "back", or "escape"
    """
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    style = TextStyle(
        font_size=screen.scaled_font_size(20),
        color=Colors.BLACK,
        align=TextAlign.LEFT,
    )
    
    while True:
        screen.fill()
        pg.mouse.set_visible(False)
        
        text_renderer.draw_text_block(
            text,
            rel_x=0.05,
            rel_y=0.05,
            max_width=screen.abs_x(0.90),
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
                elif event.key == pg.K_RIGHT:
                    return "next"
                elif event.key == pg.K_LEFT and allow_back:
                    return "back"


def _show_consent_choice(win: pg.Surface) -> tuple[str, bool]:
    """
    Display consent agreement choice with buttons.
    
    Returns:
        Tuple of (action: "next"|"back"|"escape", consented: bool)
    """
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    question = (
        'By clicking "I consent" below, you confirm that you have read the consent form, '
        'are at least 18 years old, and agree to participate in the research.\n\nWe will '
        'provide you a paper copy of this consent form upon completion of the study.\n\n'
        'By selecting "I do **not** consent" you will not be able to participate in this '
        'research and we thank you for your consideration.\n\nYou may use the arrow keys '
        'to review the information in this consent form before making a decision.'
    )
    
    # Create buttons (positions will be updated dynamically based on text height)
    agree_style = ButtonStyle(bg_color=Colors.WHITE, text_color=Colors.BLACK)
    disagree_style = ButtonStyle(bg_color=Colors.WHITE, text_color=Colors.BLACK)
    submit_style = ButtonStyle(bg_color=Colors.WHITE, text_color=Colors.BLACK)
    
    agree_btn = Button(
        screen, "I consent",
        rel_x=0.5, rel_y=0.5,
        rel_width=0.4, rel_height=0.06,
        style=agree_style,
    )
    
    disagree_btn = Button(
        screen, "I do **not** consent",
        rel_x=0.5, rel_y=0.6,
        rel_width=0.4, rel_height=0.06,
        style=disagree_style,
    )
    
    submit_btn = Button(
        screen, "Submit",
        rel_x=0.5, rel_y=0.8,
        rel_width=0.15, rel_height=0.06,
        style=submit_style,
    )
    
    selected = None  # Track which option is selected
    
    while True:
        screen.fill()
        pg.mouse.set_visible(True)
        
        # Draw question text
        text_style = TextStyle(
            font_size=screen.scaled_font_size(20),
            color=Colors.BLACK,
            align=TextAlign.LEFT,
        )
        text_end_y = text_renderer.draw_text_block(
            question,
            rel_x=0.05,
            rel_y=0.05,
            max_width=screen.abs_x(0.92),
            style=text_style,
            auto_fit=True,
            rel_max_y=0.55,
        )
        
        # Position buttons dynamically below the text, scaling to fit
        screen_bottom = screen.abs_y(0.95)
        available = screen_bottom - text_end_y
        # 3 buttons + 4 gaps (gap, btn, gap, btn, 2*gap, btn)
        desired_gap = screen.abs_y(0.03)
        desired_btn_h = screen.abs_y(0.06)
        total_needed = 3 * desired_btn_h + 4 * desired_gap
        scale = min(1.0, available / total_needed) if total_needed > 0 else 1.0
        btn_gap = int(desired_gap * scale)
        btn_height = int(desired_btn_h * scale)
        
        agree_y = text_end_y + btn_gap + btn_height // 2
        disagree_y = agree_y + btn_height + btn_gap
        submit_y = disagree_y + btn_height + int(btn_gap * 2)
        
        agree_btn.update_position(x=screen.abs_x(0.5), y=agree_y)
        disagree_btn.update_position(x=screen.abs_x(0.5), y=disagree_y)
        submit_btn.update_position(x=screen.abs_x(0.5), y=submit_y)
        agree_btn.rect.height = btn_height
        disagree_btn.rect.height = btn_height
        submit_btn.rect.height = btn_height
        
        # Update button borders and selection based on selection
        if selected == "agree":
            agree_btn.selected = True
            disagree_btn.selected = False
            agree_btn.style.border_color = Colors.BLUE
            agree_btn.style.border_width = 4
            disagree_btn.style.border_color = Colors.BLACK
            disagree_btn.style.border_width = 2
        elif selected == "disagree":
            agree_btn.selected = False
            disagree_btn.selected = True
            agree_btn.style.border_color = Colors.BLACK
            agree_btn.style.border_width = 2
            disagree_btn.style.border_color = Colors.BLUE
            disagree_btn.style.border_width = 4
        else:
            agree_btn.selected = False
            disagree_btn.selected = False
        
        # Get mouse state
        mouse_pos = pg.mouse.get_pos()
        
        # Update button states
        agree_btn.update_state(mouse_pos)
        disagree_btn.update_state(mouse_pos)
        submit_btn.update_state(mouse_pos)
        
        # Draw buttons
        agree_btn.draw()
        disagree_btn.draw()
        submit_btn.draw()
        
        screen.update()
        
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()
                elif event.key == pg.K_LEFT:
                    return ("back", False)
            
            elif event.type == pg.MOUSEBUTTONUP:
                if agree_btn.is_clicked(mouse_pos, True):
                    selected = "agree"
                elif disagree_btn.is_clicked(mouse_pos, True):
                    selected = "disagree"
                elif submit_btn.is_clicked(mouse_pos, True) and selected:
                    return ("next", selected == "agree")


def _show_email_consent(win: pg.Surface) -> tuple[str, bool]:
    """
    Display email consent screen.
    
    Returns:
        Tuple of (action: "next"|"back", email_consented: bool)
    """
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    question = (
        'May we use your email address to contact you about future research studies?\n\n'
        'This is optional and will not affect your participation or compensation in the '
        'current study. You can withdraw this permission at any time by contacting the '
        'researchers.\n\n'
        'By selecting "Yes...", you agree to be contacted about future research opportunities. '
        'By selecting "No...", we will not contact you for future studies.'
    )
    
    btn_style = ButtonStyle(bg_color=Colors.WHITE, text_color=Colors.BLACK)
    
    yes_btn = Button(
        screen, "Yes, you may contact me about future studies",
        rel_x=0.5, rel_y=0.5,
        rel_width=0.4, rel_height=0.06,
        style=ButtonStyle(bg_color=Colors.WHITE, text_color=Colors.BLACK),
    )
    
    no_btn = Button(
        screen, "No, please do not contact me",
        rel_x=0.5, rel_y=0.6,
        rel_width=0.4, rel_height=0.06,
        style=ButtonStyle(bg_color=Colors.WHITE, text_color=Colors.BLACK),
    )
    
    submit_btn = Button(
        screen, "Submit",
        rel_x=0.5, rel_y=0.8,
        rel_width=0.15, rel_height=0.06,
        style=ButtonStyle(bg_color=Colors.WHITE, text_color=Colors.BLACK),
    )
    
    selected = None
    
    while True:
        screen.fill()
        pg.mouse.set_visible(True)
        
        text_style = TextStyle(
            font_size=screen.scaled_font_size(20),
            color=Colors.BLACK,
            align=TextAlign.LEFT,
        )
        text_end_y = text_renderer.draw_text_block(
            question,
            rel_x=0.05,
            rel_y=0.05,
            max_width=screen.abs_x(0.9),
            style=text_style,
            auto_fit=True,
            rel_max_y=0.55,
        )
        
        # Position buttons dynamically below the text, scaling to fit
        screen_bottom = screen.abs_y(0.95)
        available = screen_bottom - text_end_y
        desired_gap = screen.abs_y(0.03)
        desired_btn_h = screen.abs_y(0.06)
        total_needed = 3 * desired_btn_h + 4 * desired_gap
        scale = min(1.0, available / total_needed) if total_needed > 0 else 1.0
        btn_gap = int(desired_gap * scale)
        btn_height = int(desired_btn_h * scale)
        
        yes_y = text_end_y + btn_gap + btn_height // 2
        no_y = yes_y + btn_height + btn_gap
        submit_y = no_y + btn_height + int(btn_gap * 2)
        
        yes_btn.update_position(x=screen.abs_x(0.5), y=yes_y)
        no_btn.update_position(x=screen.abs_x(0.5), y=no_y)
        submit_btn.update_position(x=screen.abs_x(0.5), y=submit_y)
        yes_btn.rect.height = btn_height
        no_btn.rect.height = btn_height
        submit_btn.rect.height = btn_height
        
        # Update button borders and selection based on selection
        if selected == "yes":
            yes_btn.selected = True
            no_btn.selected = False
            yes_btn.style.border_color = Colors.ORANGE
            yes_btn.style.border_width = 4
            no_btn.style.border_color = Colors.BLACK
            no_btn.style.border_width = 2
        elif selected == "no":
            yes_btn.selected = False
            no_btn.selected = True
            yes_btn.style.border_color = Colors.BLACK
            yes_btn.style.border_width = 2
            no_btn.style.border_color = Colors.ORANGE
            no_btn.style.border_width = 4
        else:
            yes_btn.selected = False
            no_btn.selected = False
        
        mouse_pos = pg.mouse.get_pos()
        
        yes_btn.update_state(mouse_pos)
        no_btn.update_state(mouse_pos)
        submit_btn.update_state(mouse_pos)
        
        yes_btn.draw()
        no_btn.draw()
        submit_btn.draw()
        
        screen.update()
        
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()
                elif event.key == pg.K_LEFT:
                    return ("back", False)
            
            elif event.type == pg.MOUSEBUTTONUP:
                if yes_btn.is_clicked(mouse_pos, True):
                    selected = "yes"
                elif no_btn.is_clicked(mouse_pos, True):
                    selected = "no"
                elif submit_btn.is_clicked(mouse_pos, True) and selected:
                    return ("next", selected == "yes")


def _get_signature(win: pg.Surface) -> str:
    """Get participant signature to confirm consent."""
    prompt = (
        "Please type your name to confirm that you consent to participate in this study. "
        "Press **Enter** or **Return** to submit.\n\n"
        "**Signature**"
    )
    return _get_subject_input(
        win,
        prompt=prompt,
        mode=InputMode.ALPHANUMERIC_SPACES,
        placeholder="Type your name..."
    )


# =============================================================================
# MAIN CONSENT FLOW
# =============================================================================

def run_consent(win: pg.Surface, subject_info: dict) -> bool:
    """
    Run the complete consent flow.
    
    Args:
        win: pygame surface
        subject_info: dict with subject_name, subject_number, subject_email, experimenter_name
    
    Returns:
        True if participant consented, False otherwise
    """
    # Event logging
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    save_folder = os.path.join(base_dir, 'results', subject_info['subject_number'])
    screen_logger = ScreenEventLogger('consent_flow', save_folder, subject_info['subject_number'])
    
    page_names = ['study_info', 'incentives', 'risks_benefits', 'confidentiality', 'contacts']
    pages = [
        (studyInfoText, False),       # Page 0: Study info (no back)
        (incentivesText, True),       # Page 1: Incentives
        (risksAndBenefitsText, True), # Page 2: Risks & benefits
        (confidentialityText, True),  # Page 3: Confidentiality
        (contactsAndQuestionsText, True),  # Page 4: Contacts
    ]
    
    index = 0
    consented = False
    email_consent = False
    signature = ""
    
    while True:
        if index < len(pages):
            # Show text pages
            text, allow_back = pages[index]
            result = _show_text_page(win, text, allow_back=allow_back)
            screen_logger.log_event('page_navigation', f'{page_names[index]}_{result}')
            
            if result == "next":
                index += 1
            elif result == "back" and index > 0:
                index -= 1
        
        elif index == len(pages):
            # Consent choice page
            result, consented = _show_consent_choice(win)
            screen_logger.log_event('consent_choice', f'consented={consented}_{result}')
            
            if result == "next":
                if consented:
                    index += 1  # Move to email consent
                else:
                    screen_logger.save()
                    return False  # Did not consent
            elif result == "back":
                index -= 1
        
        elif index == len(pages) + 1:
            # Email consent page
            result, email_consent = _show_email_consent(win)
            screen_logger.log_event('email_consent', f'email_consent={email_consent}_{result}')
            
            if result == "next":
                index += 1  # Move to signature
            elif result == "back":
                index -= 1
        
        elif index == len(pages) + 2:
            # Signature page
            signature = _get_signature(win)
            if signature:
                screen_logger.log_event('signature', 'signed')
                screen_logger.save()
                # All done - save consent data and return
                _save_consent_data(
                    subject_info,
                    consented=True,
                    email_consent=email_consent,
                    signature=signature,
                )
                return True
            # If no signature, stay on this page
        
        else:
            break
    
    screen_logger.save()
    return consented


def _save_consent_data(
    subject_info: dict,
    consented: bool,
    email_consent: bool,
    signature: str,
) -> None:
    """Save consent data to file."""
    import csv
    from datetime import datetime
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    save_folder = os.path.join(base_dir, 'results', subject_info['subject_number'])
    os.makedirs(save_folder, exist_ok=True)
    
    filepath = os.path.join(save_folder, f"consent_{subject_info['subject_number']}.csv")
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Subject Number', 'Subject Name', 'Experimenter', 'Consented', 'Email Consent', 'Signature', 'Timestamp'])
        writer.writerow([
            subject_info['subject_number'],
            subject_info['subject_name'],
            subject_info['experimenter_name'],
            consented,
            email_consent,
            signature,
            datetime.now().isoformat()
        ])


def show_non_consent(win: pg.Surface) -> None:
    """Show the non-consent screen and exit the experiment."""
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    
    style = TextStyle(
        font_size=screen.scaled_font_size(20),
        color=Colors.BLACK,
        align=TextAlign.LEFT,
    )
    
    while True:
        screen.fill()
        pg.mouse.set_visible(False)
        
        text_renderer.draw_text_block(
            nonConsentText,
            rel_x=0.05,
            rel_y=0.05,
            max_width=screen.abs_x(0.90),
            style=style,
            auto_fit=True,
            rel_max_y=0.95,
        )
        
        screen.update()
        
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE or event.key == pg.K_ESCAPE:
                    pg.quit()
                    return