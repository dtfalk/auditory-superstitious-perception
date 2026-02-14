"""
Setup Subtimeline
=================
Handles initialization of pygame, audio device selection, and window creation.
"""

import os
import sys
import argparse
import numpy as np
import pygame as pg
import sounddevice as sd

# Import from experiment_helpers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.audioEngine import AudioEngine
from utils.displayEngine import (
    Screen, TextRenderer, Colors, Color, TextStyle, TextAlign,
)


# =============================================================================
# AUDIO DEVICE HELPERS
# =============================================================================

def _get_output_devices() -> list[tuple[int, str]]:
    """
    Return a list of (device_index, device_name) for every output-capable device.
    """
    devs = sd.query_devices()
    output_devices: list[tuple[int, str]] = []
    for i, d in enumerate(devs):
        if d["max_output_channels"] > 0:
            output_devices.append((i, d["name"]))
    return output_devices


def _get_default_device_index(devices: list[tuple[int, str]]) -> int:
    """
    Return the list-position of the system default output device inside
    *devices*, or 0 if it cannot be determined.
    """
    try:
        default_out = sd.default.device[1]
        if default_out is not None and default_out >= 0:
            for pos, (dev_idx, _) in enumerate(devices):
                if dev_idx == default_out:
                    return pos
    except Exception:
        pass
    return 0


# =============================================================================
# LAST-USED DEVICE PERSISTENCE
# =============================================================================

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LAST_DEVICE_FILE = os.path.join(_PROJECT_ROOT, '.last_audio_device')


def _load_last_device() -> str | None:
    """Return the device name saved from the previous session, or None."""
    try:
        with open(_LAST_DEVICE_FILE, 'r', encoding='utf-8') as f:
            name = f.read().strip()
            return name if name else None
    except FileNotFoundError:
        return None


def _save_last_device(device_name: str) -> None:
    """Persist the chosen device name so the next session can highlight it."""
    try:
        with open(_LAST_DEVICE_FILE, 'w', encoding='utf-8') as f:
            f.write(device_name)
    except Exception as e:
        print(f"Could not save last audio device: {e}")


def _get_best_preselect(devices: list[tuple[int, str]]) -> int:
    """
    Return the list-position to pre-select:
    1) last-used device (if still present), else
    2) system default output, else
    3) first device.
    """
    last_name = _load_last_device()
    if last_name:
        for pos, (_, name) in enumerate(devices):
            if name == last_name:
                return pos
    return _get_default_device_index(devices)


# =============================================================================
# TEST TONE
# =============================================================================

def _play_test_tone(device_index: int, duration: float = 0.8, freq: float = 440.0, fs: int = 44100) -> None:
    """
    Play a short sine-wave beep through the given device using sounddevice.

    Non-blocking — the tone plays in the background and stops automatically.
    Any previous test tone is stopped before the new one starts.
    """
    try:
        sd.stop()  # stop any previous test tone
        t = np.linspace(0, duration, int(fs * duration), endpoint=False, dtype=np.float32)
        # Apply a short fade-in / fade-out to avoid clicks
        fade_samples = int(fs * 0.02)
        tone = 0.35 * np.sin(2.0 * np.pi * freq * t)
        tone[:fade_samples] *= np.linspace(0, 1, fade_samples, dtype=np.float32)
        tone[-fade_samples:] *= np.linspace(1, 0, fade_samples, dtype=np.float32)
        sd.play(tone, samplerate=fs, device=device_index)
    except Exception as e:
        print(f"Test tone failed on device {device_index}: {e}")


# =============================================================================
# AUDIO DEVICE SELECTION SCREEN
# =============================================================================

def _show_audio_device_selection(
    win: pg.Surface,
    devices: list[tuple[int, str]],
    pre_selected: int = 0,
) -> int:
    """
    Display a fullscreen device-selection screen with radio buttons.

    Args:
        win: pygame surface (already created)
        devices: list of (device_index, device_name)
        pre_selected: list-position to highlight by default

    Returns:
        The sounddevice device index chosen by the user.
    """
    pg.mouse.set_visible(True)
    screen = Screen(win)
    text_renderer = TextRenderer(screen)
    selected_pos = pre_selected

    # Determine which device was used last session (for annotation)
    last_used_name = _load_last_device()

    # Sizing constants
    title_style = TextStyle(
        font_size=screen.scaled_font_size(16),
        color=Colors.BLACK,
        align=TextAlign.CENTER,
        bold=True,
    )
    instruction_style = TextStyle(
        font_size=screen.scaled_font_size(30),
        color=Colors.DARK_GRAY,
        align=TextAlign.CENTER,
    )
    label_font_size = max(14, screen.height // 42)
    radio_radius = max(8, screen.height // 70)
    row_height = max(label_font_size + 12, int(screen.height * 0.04))

    # Scrolling state
    scroll_offset = 0
    # Test-tone state: track which device is being tested & when it started
    test_device_pos: int | None = None
    test_start_ticks: int = 0
    test_duration_ms: int = 800  # matches _play_test_tone default duration

    while True:
        screen.fill()

        # ── Title ──
        title_bottom = text_renderer.draw_centered_text(
            "**Select Audio Output Device**",
            rel_y=0.03,
            style=title_style,
        )

        # ── Instruction text ──
        instr1_bottom = text_renderer.draw_centered_text(
            "Select the correct audio output device from the list below.",
            rel_y=title_bottom / screen.height + 0.02,
            style=instruction_style,
        )
        instr2_bottom = text_renderer.draw_centered_text(
            'Use the **Test Sound** button (or press **T**) to verify audio plays through the intended device before confirming.',
            rel_y=instr1_bottom / screen.height + 0.01,
            style=instruction_style,
        )

        # ── Compute list area (starts below instruction text) ──
        list_top = instr2_bottom + screen.abs_y(0.02)
        list_bottom = screen.abs_y(0.85)
        list_left = screen.abs_x(0.06)
        visible_height = list_bottom - list_top

        # Total content height
        total_content_height = len(devices) * row_height

        # Clamp scroll
        max_scroll = max(0, total_content_height - visible_height)
        scroll_offset = max(0, min(scroll_offset, max_scroll))

        # ── Draw device rows (clipped to list area) ──
        label_font = pg.font.SysFont("times new roman", label_font_size)
        mouse_pos = pg.mouse.get_pos()
        row_rects: list[tuple[pg.Rect, int]] = []  # (hit_rect, list_pos)

        for pos, (dev_idx, dev_name) in enumerate(devices):
            row_y = list_top + pos * row_height - scroll_offset

            # Skip rows outside the visible band
            if row_y + row_height < list_top or row_y > list_bottom:
                continue

            # Radio circle centre
            cx = list_left + radio_radius
            cy = row_y + row_height // 2

            # Hit rectangle spanning the full row width
            hit_rect = pg.Rect(list_left, row_y, screen.abs_x(0.88), row_height)
            row_rects.append((hit_rect, pos))

            # Hover highlight
            if hit_rect.collidepoint(mouse_pos):
                highlight_surf = pg.Surface((hit_rect.width, hit_rect.height), pg.SRCALPHA)
                highlight_surf.fill((0, 0, 0, 18))
                win.blit(highlight_surf, hit_rect.topleft)

            # Selected highlight band
            if pos == selected_pos:
                sel_surf = pg.Surface((hit_rect.width, hit_rect.height), pg.SRCALPHA)
                sel_surf.fill((50, 50, 255, 30))
                win.blit(sel_surf, hit_rect.topleft)

            # Outer radio circle
            pg.draw.circle(win, Colors.BLACK.to_tuple(), (cx, cy), radio_radius, 2)
            # Filled inner circle when selected
            if pos == selected_pos:
                pg.draw.circle(win, Colors.BLUE.to_tuple(), (cx, cy), radio_radius - 4)

            # Device name label (annotate if this was the last-used device)
            text_x = cx + radio_radius + 12
            text_y = cy - label_font.get_height() // 2
            is_last_used = last_used_name and dev_name == last_used_name

            name_surf = label_font.render(dev_name, True, Colors.BLACK.to_tuple())
            win.blit(name_surf, (text_x, text_y))

            if is_last_used:
                tag_x = text_x + name_surf.get_width() + 12
                tag_surf = label_font.render("(last used)", True, Colors.BLUE.to_tuple())
                win.blit(tag_surf, (tag_x, text_y))

        # ── Scrollbar (only if content overflows) ──
        if total_content_height > visible_height:
            sb_x = screen.abs_x(0.96)
            sb_w = 6
            thumb_ratio = visible_height / total_content_height
            thumb_h = max(20, int(visible_height * thumb_ratio))
            thumb_y = list_top + int((scroll_offset / max_scroll) * (visible_height - thumb_h)) if max_scroll > 0 else list_top
            pg.draw.rect(win, Colors.LIGHT_GRAY.to_tuple(), (sb_x, list_top, sb_w, visible_height))
            pg.draw.rect(win, Colors.DARK_GRAY.to_tuple(), (sb_x, thumb_y, sb_w, thumb_h))

        # ── Check if test tone is still playing ──
        now_ticks = pg.time.get_ticks()
        tone_playing = (test_device_pos is not None) and (now_ticks - test_start_ticks < test_duration_ms)
        if not tone_playing:
            test_device_pos = None

        # ── Bottom buttons: Test Sound  |  Confirm Selection ──
        btn_font = pg.font.SysFont("times new roman", max(16, screen.height // 38))
        btn_h = screen.abs_y(0.06)
        btn_y = screen.abs_y(0.89)
        gap = screen.abs_x(0.03)

        # Test Sound button
        test_w = screen.abs_x(0.18)
        test_rect = pg.Rect(0, btn_y, test_w, btn_h)
        # Confirm button
        conf_w = screen.abs_x(0.20)
        conf_rect = pg.Rect(0, btn_y, conf_w, btn_h)
        # Centre the pair
        total_w = test_w + gap + conf_w
        start_x = (screen.width - total_w) // 2
        test_rect.x = start_x
        conf_rect.x = start_x + test_w + gap

        # Draw Test Sound button
        test_hovered = test_rect.collidepoint(mouse_pos)
        if tone_playing:
            test_color = Colors.GREEN.darken(0.7)
        elif test_hovered:
            test_color = Colors.GREEN.darken(0.85)
        else:
            test_color = Colors.GREEN
        pg.draw.rect(win, test_color.to_tuple(), test_rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), test_rect, 2)
        test_label = "Playing..." if tone_playing else "Test Sound"
        test_surf = btn_font.render(test_label, True, Colors.WHITE.to_tuple())
        win.blit(test_surf, test_surf.get_rect(center=test_rect.center))

        # Draw Confirm Selection button
        conf_hovered = conf_rect.collidepoint(mouse_pos)
        conf_color = Colors.BLUE.darken(0.85) if conf_hovered else Colors.BLUE
        pg.draw.rect(win, conf_color.to_tuple(), conf_rect)
        pg.draw.rect(win, Colors.BLACK.to_tuple(), conf_rect, 2)
        conf_surf = btn_font.render("Confirm Selection", True, Colors.WHITE.to_tuple())
        win.blit(conf_surf, conf_surf.get_rect(center=conf_rect.center))

        screen.update()

        # ── Events ──
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()
                elif event.key == pg.K_UP and selected_pos > 0:
                    selected_pos -= 1
                    # Auto-scroll to keep selection visible
                    sel_y = list_top + selected_pos * row_height - scroll_offset
                    if sel_y < list_top:
                        scroll_offset = max(0, selected_pos * row_height)
                elif event.key == pg.K_DOWN and selected_pos < len(devices) - 1:
                    selected_pos += 1
                    sel_y = list_top + selected_pos * row_height - scroll_offset
                    if sel_y + row_height > list_bottom:
                        scroll_offset = min(max_scroll, (selected_pos + 1) * row_height - visible_height)
                elif event.key == pg.K_t:
                    # T key = test currently selected device
                    _play_test_tone(devices[selected_pos][0])
                    test_device_pos = selected_pos
                    test_start_ticks = pg.time.get_ticks()
                elif event.key in (pg.K_RETURN, pg.K_KP_ENTER):
                    sd.stop()
                    pg.mouse.set_visible(False)
                    return devices[selected_pos][0]

            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:  # left click
                    # Check Test Sound button
                    if test_rect.collidepoint(event.pos) and not tone_playing:
                        _play_test_tone(devices[selected_pos][0])
                        test_device_pos = selected_pos
                        test_start_ticks = pg.time.get_ticks()
                    # Check confirm button
                    elif conf_rect.collidepoint(event.pos):
                        sd.stop()
                        pg.mouse.set_visible(False)
                        return devices[selected_pos][0]
                    # Check radio rows
                    for hit_rect, pos in row_rects:
                        if hit_rect.collidepoint(event.pos):
                            selected_pos = pos
                            break
                elif event.button == 4:  # scroll up
                    scroll_offset = max(0, scroll_offset - row_height)
                elif event.button == 5:  # scroll down
                    scroll_offset = min(max_scroll, scroll_offset + row_height)

            elif event.type == pg.MOUSEWHEEL:
                scroll_offset = max(0, min(max_scroll, scroll_offset - event.y * row_height))


# =============================================================================
# LEGACY AUTO-SELECTION (kept as fallback for --audio-device / --dev-speakers)
# =============================================================================

def pick_output_device(
    prefer_substrings: tuple[str, ...] = ("Speakers", "Realtek"),
    exclude_substrings: tuple[str, ...] = (),
    skip_default: bool = False,
) -> tuple[int, str]:
    """
    Auto-select the best audio output device (used by CLI overrides).
    """
    devs = sd.query_devices()
    hostapis = sd.query_hostapis()
    wasapi_ids = [i for i, api in enumerate(hostapis) if "WASAPI" in api["name"].upper()]
    wasapi_id = wasapi_ids[0] if wasapi_ids else None

    def _name_ok(name: str) -> bool:
        lname = name.lower()
        for bad in exclude_substrings:
            if bad and bad.lower() in lname:
                return False
        return True

    if not skip_default:
        default_out = sd.default.device[1]
        if default_out is not None and default_out >= 0:
            d = devs[default_out]
            if d["max_output_channels"] > 0 and _name_ok(d["name"]):
                return default_out, d["name"]

    if wasapi_id is not None:
        candidates = [
            (i, d["name"]) for i, d in enumerate(devs)
            if d["max_output_channels"] > 0 and d["hostapi"] == wasapi_id and _name_ok(d["name"])
        ]
        for substr in prefer_substrings:
            for i, name in candidates:
                if substr.lower() in name.lower():
                    return i, name
        if candidates:
            return candidates[0]

    for i, d in enumerate(devs):
        if d["max_output_channels"] > 0 and _name_ok(d["name"]):
            return i, d["name"]

    raise RuntimeError("No output devices found")


# =============================================================================
# SETUP HELPERS
# =============================================================================

def set_high_priority() -> None:
    """Set the process to high priority on Windows for better audio performance."""
    if sys.platform != "win32":
        return
    try:
        import psutil
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS)
    except Exception as e:
        print("Could not set HIGH priority:", e)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--audio-device",
        type=int,
        default=None,
        help="Force a specific sounddevice output device index (overrides GUI selection).",
    )
    parser.add_argument(
        "--dev-speakers",
        action="store_true",
        help="Dev mode: bypass system default (often HDMI) and prefer built-in laptop speakers.",
    )
    return parser.parse_args()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def run_setup(
    args: argparse.Namespace | None = None,
    win_width: int | None = None,
    win_height: int | None = None,
) -> tuple[pg.Surface, AudioEngine]:
    """
    Initialize pygame, show the audio-device picker, and create the experiment window.

    The GUI selection screen is shown unless ``--audio-device`` or
    ``--dev-speakers`` is passed on the command line.

    Returns:
        Tuple of (pygame window surface, AudioEngine instance)
    """
    if args is None:
        args = parse_args()

    # Import screen dimensions from experimenterLevers
    if win_width is None or win_height is None:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'experiment_helpers'))
        from experiment_helpers.experimenterLevers import WIN_WIDTH, WIN_HEIGHT
        win_width = win_width or WIN_WIDTH
        win_height = win_height or WIN_HEIGHT

    # Set high priority for better audio performance
    set_high_priority()

    # Initialize pygame
    pg.init()

    # Create fullscreen window first (needed for the selection screen)
    win = pg.display.set_mode((win_width, win_height), pg.FULLSCREEN)
    pg.mouse.set_visible(False)

    # ── Determine audio device ──
    env_dev = os.getenv("ASP_DEV_SPEAKERS", "").strip().lower() in {"1", "true", "yes", "on"}
    dev_speakers = bool(args.dev_speakers or env_dev)

    if args.audio_device is not None:
        # CLI override — skip GUI
        audio_device = int(args.audio_device)
        dev_name = sd.query_devices(audio_device)["name"]
    elif dev_speakers:
        # Dev-speakers shortcut — skip GUI
        audio_device, dev_name = pick_output_device(
            prefer_substrings=("Speakers", "Realtek", "Internal"),
            exclude_substrings=("HDMI", "NVIDIA", "Intel", "Display", "Monitor"),
            skip_default=True,
        )
    else:
        # ── Interactive GUI selection ──
        devices = _get_output_devices()
        if not devices:
            raise RuntimeError("No audio output devices found")
        best_pos = _get_best_preselect(devices)
        audio_device = _show_audio_device_selection(win, devices, pre_selected=best_pos)
        dev_name = sd.query_devices(audio_device)["name"]

    print("Using output:", audio_device, dev_name)

    # Persist chosen device for next session
    _save_last_device(dev_name)

    # Create audio engine with the chosen device
    audio_engine = AudioEngine(device_index=audio_device, samplerate=44100, blocksize=256)

    return win, audio_engine
