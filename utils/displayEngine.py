"""
displayEngine.py - Modular Display Engine for Experimental Screens

A comprehensive, modular system for building experimental psychology screens.
Provides building blocks for:
- Screen/canvas management
- Rich text rendering (bold, italic, alignment, wrapping)
- Configurable text input (letters, numbers, spaces, special chars)
- Reusable buttons and interactive elements
- Grid layouts for complex screens
- Screen composition utilities

Usage:
    from displayEngine import (
        Screen, TextRenderer, TextInput, Button, ButtonStyle, 
        GridLayout, ScreenBuilder
    )
"""

from __future__ import annotations
import re
import pygame as pg
import sys
from typing import Callable, Any
from dataclasses import dataclass, field, replace as _dc_replace
from enum import Enum, auto

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

# Default font family used throughout the engine
DEFAULT_FONT_FAMILY = "times new roman"

# Shift key mappings for special characters
SHIFT_KEY_MAP = {
    ord('1'): '!', ord('2'): '@', ord('3'): '#', ord('4'): '$', 
    ord('5'): '%', ord('6'): '^', ord('7'): '&', ord('8'): '*',
    ord('9'): '(', ord('0'): ')', ord('-'): '_', ord('='): '+',
    ord('['): '{', ord(']'): '}', ord('\\'): '|', ord(';'): ':',
    ord("'"): '"', ord(','): '<', ord('.'): '>', ord('/'): '?',
    ord('`'): '~',
}

# =============================================================================
# ENUMERATIONS
# =============================================================================

class TextAlign(Enum):
    """Text alignment options."""
    LEFT = auto()
    CENTER = auto()
    RIGHT = auto()


class VerticalAlign(Enum):
    """Vertical alignment options."""
    TOP = auto()
    CENTER = auto()
    BOTTOM = auto()


class InputMode(Enum):
    """Input mode restrictions for text input."""
    LETTERS_ONLY = auto()        # a-z, A-Z
    NUMBERS_ONLY = auto()        # 0-9
    ALPHANUMERIC = auto()        # a-z, A-Z, 0-9
    ALPHANUMERIC_SPACES = auto() # a-z, A-Z, 0-9, space
    EMAIL = auto()               # a-z, 0-9, @, ., -
    FULL_ASCII = auto()          # All printable ASCII (32-126)
    CUSTOM = auto()              # Use custom validator


class ButtonState(Enum):
    """Button visual states."""
    NORMAL = auto()
    HOVERED = auto()
    PRESSED = auto()
    DISABLED = auto()
    SELECTED = auto()  # Persistent selection (e.g., radio button)


# =============================================================================
# DATA CLASSES - Styles & Configuration
# =============================================================================

@dataclass
class Color:
    """RGB color with helper methods."""
    r: int = 0
    g: int = 0
    b: int = 0
    
    def to_tuple(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)
    
    def darken(self, factor: float = 0.6) -> 'Color':
        return Color(
            int(self.r * factor),
            int(self.g * factor),
            int(self.b * factor)
        )
    
    def lighten(self, factor: float = 1.4) -> 'Color':
        return Color(
            min(255, int(self.r * factor)),
            min(255, int(self.g * factor)),
            min(255, int(self.b * factor))
        )


# Predefined colors
class Colors:
    """Predefined color palette."""
    BLACK = Color(0, 0, 0)
    WHITE = Color(255, 255, 255)
    GRAY = Color(128, 128, 128)
    DARK_GRAY = Color(64, 64, 64)
    LIGHT_GRAY = Color(192, 192, 192)
    RED = Color(255, 50, 50)
    GREEN = Color(0, 128, 0)
    BLUE = Color(50, 50, 255)
    YELLOW = Color(255, 255, 0)
    ORANGE = Color(255, 165, 0)
    BACKGROUND = Color(128, 128, 128)


@dataclass
class TextStyle:
    """Style configuration for text rendering."""
    font_family: str = DEFAULT_FONT_FAMILY
    font_size: int = 24
    color: Color = field(default_factory=lambda: Colors.BLACK)
    bold: bool = False
    italic: bool = False
    underline: bool = False
    align: TextAlign = TextAlign.LEFT
    line_spacing: float = 1.15  # Multiplier of font height (can reduce to 1.0 for tight spacing)


@dataclass
class ButtonStyle:
    """Style configuration for buttons."""
    bg_color: Color = field(default_factory=lambda: Colors.BLUE)
    text_color: Color = field(default_factory=lambda: Colors.WHITE)
    border_color: Color = field(default_factory=lambda: Colors.BLACK)
    border_width: int = 2
    disabled_bg_color: Color = field(default_factory=lambda: Colors.GRAY)
    disabled_text_color: Color = field(default_factory=lambda: Colors.DARK_GRAY)
    hover_darken: float = 0.85
    pressed_darken: float = 0.7
    selected_darken: float = 0.8  # Darken factor when selected
    font_family: str = DEFAULT_FONT_FAMILY
    font_size: int | None = None  # None = auto-scale
    padding_x: float = 0.02  # As fraction of screen width
    padding_y: float = 0.01  # As fraction of screen height
    corner_radius: int = 0  # 0 = no rounding


@dataclass
class InputStyle:
    """Style configuration for text input fields."""
    bg_color: Color = field(default_factory=lambda: Colors.WHITE)
    text_color: Color = field(default_factory=lambda: Colors.BLACK)
    border_color: Color = field(default_factory=lambda: Colors.BLACK)
    border_width: int = 2
    cursor_color: Color = field(default_factory=lambda: Colors.BLACK)
    placeholder_color: Color = field(default_factory=lambda: Colors.GRAY)
    font_family: str = DEFAULT_FONT_FAMILY
    font_size: int | None = None  # None = auto-scale
    padding: int = 10


# =============================================================================
# CORE CLASSES
# =============================================================================

class Screen:
    """
    Core screen/canvas management class.
    
    Provides the foundation for all display operations including:
    - Background filling
    - Coordinate conversions (relative <-> absolute)
    - Screen dimension queries
    - Event handling coordination
    
    Usage:
        screen = Screen(pygame_surface)
        screen.fill()
        screen.update()
    """
    
    def __init__(self, win: pg.Surface, background_color: Color = Colors.BACKGROUND):
        self.win = win
        self.background_color = background_color
        self._width, self._height = self._get_dimensions()
    
    def _get_dimensions(self) -> tuple[int, int]:
        """Get current window dimensions."""
        surface = pg.display.get_surface()
        if surface:
            return surface.get_size()
        try:
            return self.win.get_size()
        except Exception:
            return 800, 600  # Fallback
    
    @property
    def width(self) -> int:
        """Current screen width."""
        return self._width
    
    @property
    def height(self) -> int:
        """Current screen height."""
        return self._height
    
    @property 
    def center(self) -> tuple[int, int]:
        """Center point of the screen."""
        return (self.width // 2, self.height // 2)
    
    def refresh_dimensions(self) -> None:
        """Update cached dimensions (call after window resize)."""
        self._width, self._height = self._get_dimensions()
    
    def fill(self, color: Color | None = None) -> None:
        """Fill screen with background color."""
        c = color or self.background_color
        self.win.fill(c.to_tuple())
    
    def update(self) -> None:
        """Update the display (flip buffer)."""
        pg.display.flip()
    
    def abs_x(self, rel_x: float) -> int:
        """Convert relative x (0.0-1.0) to absolute pixels."""
        return int(rel_x * self.width)
    
    def abs_y(self, rel_y: float) -> int:
        """Convert relative y (0.0-1.0) to absolute pixels."""
        return int(rel_y * self.height)
    
    def abs_pos(self, rel_x: float, rel_y: float) -> tuple[int, int]:
        """Convert relative position to absolute pixels."""
        return (self.abs_x(rel_x), self.abs_y(rel_y))
    
    def rel_x(self, abs_x: int) -> float:
        """Convert absolute x pixels to relative (0.0-1.0)."""
        return abs_x / self.width if self.width > 0 else 0.0
    
    def rel_y(self, abs_y: int) -> float:
        """Convert absolute y pixels to relative (0.0-1.0)."""
        return abs_y / self.height if self.height > 0 else 0.0
    
    def scaled_font_size(self, base_divisor: int = 20) -> int:
        """Get font size scaled to current screen height."""
        return max(14, self.height // base_divisor)
    
    def handle_escape(self) -> None:
        """Standard escape handler - quit pygame and exit."""
        pg.quit()
        sys.exit()


class TextRenderer:
    """
    Rich text rendering system with support for:
    - Word wrapping
    - Text alignment (left, center, right)
    - Font styles (bold, italic, underline)
    - Multi-line text with configurable line spacing
    - Inline formatting via markup (optional)
    
    Usage:
        renderer = TextRenderer(screen)
        
        # Simple text
        renderer.draw_text("Hello World", x=100, y=100)
        
        # Styled text
        style = TextStyle(font_size=32, bold=True, align=TextAlign.CENTER)
        renderer.draw_text("Centered Bold", style=style, rel_x=0.5, rel_y=0.2)
        
        # Wrapped paragraph
        renderer.draw_paragraph(
            "Long text here...",
            max_width=600,
            style=style,
            x=100, y=200
        )
    """
    
    def __init__(self, screen: Screen):
        self.screen = screen
        self._font_cache: dict[tuple, pg.font.Font] = {}
    
    def _get_font(self, family: str, size: int, bold: bool = False, italic: bool = False) -> pg.font.Font:
        """Get or create a cached pygame font."""
        key = (family, size, bold, italic)
        if key not in self._font_cache:
            try:
                font = pg.font.SysFont(family, size, bold=bold, italic=italic)
            except Exception:
                font = pg.font.SysFont(DEFAULT_FONT_FAMILY, size, bold=bold, italic=italic)
            self._font_cache[key] = font
        return self._font_cache[key]
    
    def _wrap_text(self, text: str, font: pg.font.Font, max_width: int) -> list[str]:
        """Word-wrap text to fit within max_width pixels."""
        if not text or max_width <= 0:
            return [""] if not text else [text]
        
        words = text.split()
        if not words:
            return [""]
        
        lines = []
        current = words[0]
        
        for word in words[1:]:
            trial = f"{current} {word}"
            if font.size(trial)[0] <= max_width:
                current = trial
            else:
                # Handle case where single word exceeds max_width
                if font.size(current)[0] > max_width:
                    lines.extend(self._split_long_word(current, font, max_width))
                else:
                    lines.append(current)
                current = word
        
        # Handle last segment
        if font.size(current)[0] > max_width:
            lines.extend(self._split_long_word(current, font, max_width))
        else:
            lines.append(current)
        
        return lines
    
    def _split_long_word(self, word: str, font: pg.font.Font, max_width: int) -> list[str]:
        """Split a very long word character by character."""
        chunks = []
        current = ""
        for ch in word:
            trial = current + ch
            if font.size(trial)[0] <= max_width or not current:
                current = trial
            else:
                chunks.append(current)
                current = ch
        if current:
            chunks.append(current)
        return chunks

    # ------------------------------------------------------------------
    # Rich-text helpers:  **bold**  inline markup
    # ------------------------------------------------------------------
    _BOLD_RE = re.compile(r'\*\*(.+?)\*\*')

    @staticmethod
    def _parse_rich_segments(text: str) -> list[tuple[str, bool]]:
        """Parse a string into (text, is_bold) segments.

        ``**word**`` is rendered bold; everything else is normal.
        """
        segments: list[tuple[str, bool]] = []
        last = 0
        for m in TextRenderer._BOLD_RE.finditer(text):
            if m.start() > last:
                segments.append((text[last:m.start()], False))
            segments.append((m.group(1), True))
            last = m.end()
        if last < len(text):
            segments.append((text[last:], False))
        return segments if segments else [(text, False)]

    @staticmethod
    def _strip_bold_markers(text: str) -> str:
        """Remove ``**`` markers so width measurement uses plain text."""
        return TextRenderer._BOLD_RE.sub(r'\1', text)

    def _measure_rich_line_width(
        self, text: str, family: str, size: int, italic: bool = False,
    ) -> int:
        """Measure the rendered pixel width of *text* that may contain ``**bold**``."""
        total = 0
        for seg, bold in self._parse_rich_segments(text):
            font = self._get_font(family, size, bold=bold, italic=italic)
            total += font.size(seg)[0]
        return total

    def _render_rich_line(
        self,
        text: str,
        x: int,
        y: int,
        style: TextStyle,
        render: bool = True,
    ) -> int:
        """Render (or measure) a single line that may contain ``**bold**`` markup.

        Returns the total rendered width.
        """
        cursor = x
        for seg, bold in self._parse_rich_segments(text):
            font = self._get_font(style.font_family, style.font_size, bold=bold, italic=style.italic)
            if render:
                surf = font.render(seg, True, style.color.to_tuple())
                self.screen.win.blit(surf, (cursor, y))
            cursor += font.size(seg)[0]
        return cursor - x

    # ------------------------------------------------------------------
    # Line-metadata: leading indentation  +  >>> centre directive
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_line_meta(line: str) -> tuple[str, bool, str]:
        """Return ``(content, force_center, indentation_prefix)``.

        * Leading whitespace is preserved and measured for indentation.
        * A ``>>>`` prefix (optionally followed by a space) forces that line
          to be centred regardless of the style's ``align``.
        """
        # Detect leading whitespace
        stripped = line.lstrip()
        indent_prefix = line[:len(line) - len(stripped)]

        # Detect >>> centering directive (after stripping indent)
        force_center = False
        content = stripped
        if content.startswith('>>>'):
            force_center = True
            content = content[3:].lstrip()  # strip the >>> and optional space

        return content, force_center, indent_prefix
    
    def get_text_size(self, text: str, style: TextStyle | None = None) -> tuple[int, int]:
        """Get the pixel dimensions of rendered text."""
        style = style or TextStyle()
        font = self._get_font(style.font_family, style.font_size, style.bold, style.italic)
        return font.size(text)
    
    def draw_text(
        self,
        text: str,
        x: int | None = None,
        y: int | None = None,
        rel_x: float | None = None,
        rel_y: float | None = None,
        style: TextStyle | None = None,
        anchor: str = "topleft"
    ) -> pg.Rect:
        """
        Draw a single line of text.
        
        Args:
            text: The text to render
            x, y: Absolute pixel position (use either abs or rel)
            rel_x, rel_y: Relative position (0.0-1.0)
            style: TextStyle configuration
            anchor: Rect anchor point ('topleft', 'center', 'topright', etc.)
        
        Returns:
            The bounding rect of the rendered text
        """
        style = style or TextStyle()
        font = self._get_font(style.font_family, style.font_size, style.bold, style.italic)
        
        if style.underline:
            font.set_underline(True)
        
        surface = font.render(text, True, style.color.to_tuple())
        rect = surface.get_rect()
        
        # Determine position
        pos_x = x if x is not None else (self.screen.abs_x(rel_x) if rel_x is not None else 0)
        pos_y = y if y is not None else (self.screen.abs_y(rel_y) if rel_y is not None else 0)
        
        setattr(rect, anchor, (pos_x, pos_y))
        self.screen.win.blit(surface, rect)
        
        if style.underline:
            font.set_underline(False)
        
        return rect
    
    def _measure_paragraph_height(
        self,
        text: str,
        font: pg.font.Font,
        max_width: int,
        start_y: int,
        line_spacing: float = 1.0,
    ) -> int:
        """
        Simulate text layout and return the y position after the last line.
        Does NOT render anything — used for measuring whether text fits.

        Handles leading-whitespace indentation, ``>>>`` centre markers, and
        ``**bold**`` inline markup (stripped for sizing).
        """
        line_height = int(font.get_linesize() * line_spacing)
        paragraphs = text.split('\n')
        current_y = start_y

        for paragraph in paragraphs:
            if not paragraph.strip():
                current_y += line_height
                continue

            content, _fc, indent_prefix = self._parse_line_meta(paragraph)
            plain = self._strip_bold_markers(content)
            indent_w = font.size(indent_prefix)[0] if indent_prefix else 0
            wrap_w = max(1, max_width - indent_w)

            lines = self._wrap_text(plain, font, wrap_w)
            for _line in lines:
                current_y += line_height

        return current_y

    def auto_fit_font_size(
        self,
        text: str,
        style: TextStyle,
        max_width: int | None = None,
        rel_max_width: float | None = None,
        start_y: int | None = None,
        rel_start_y: float | None = None,
        max_y: int | None = None,
        rel_max_y: float | None = None,
        min_font_size: int = 1,
    ) -> TextStyle:
        """
        Return a copy of *style* whose font_size has been reduced (if needed)
        until the given text fits within the vertical bounds.

        The caller passes the same positional / sizing parameters that would
        later be given to ``draw_paragraph``.  The method simulates word-wrap
        layout at progressively smaller font sizes until everything fits
        between *start_y* and *max_y*.

        Args:
            text: The full text (may include ``\\n``)
            style: Starting TextStyle (its font_size is the maximum tried)
            max_width / rel_max_width: Horizontal constraint
            start_y / rel_start_y: Vertical start
            max_y / rel_max_y: Vertical limit (default 95 % of screen height)
            min_font_size: Smallest font size to try before giving up

        Returns:
            A new TextStyle with ``font_size`` adjusted to fit.
        """
        # Resolve vertical bounds
        y0 = (start_y if start_y is not None
               else self.screen.abs_y(rel_start_y) if rel_start_y is not None
               else self.screen.abs_y(0.05))
        y_max = (max_y if max_y is not None
                 else self.screen.abs_y(rel_max_y) if rel_max_y is not None
                 else self.screen.abs_y(0.95))

        # Resolve horizontal bound
        if max_width is None:
            if rel_max_width is not None:
                max_width = self.screen.abs_x(rel_max_width)
            else:
                max_width = self.screen.abs_x(0.9)

        font_size = style.font_size
        font = self._get_font(style.font_family, font_size, style.bold, style.italic)

        while font_size > min_font_size:
            end_y = self._measure_paragraph_height(
                text, font, max_width, y0, style.line_spacing
            )
            if end_y <= y_max:
                break
            font_size -= 1
            font = self._get_font(style.font_family, font_size, style.bold, style.italic)

        # Return a copy with the (possibly reduced) font size
        return _dc_replace(style, font_size=font_size)

    def draw_paragraph(
        self,
        text: str,
        max_width: int | None = None,
        rel_max_width: float | None = None,
        x: int | None = None,
        y: int | None = None,
        rel_x: float | None = None,
        rel_y: float | None = None,
        style: TextStyle | None = None,
        max_y: int | None = None,
        auto_fit: bool = False,
        rel_max_y: float | None = None,
    ) -> int:
        """
        Draw wrapped, multi-line text with rich formatting support.

        Formatting features:
        * ``**bold**``  – wraps a word or phrase in bold inline.
        * ``>>>``       – prefix a line with ``>>>`` to centre it (even in LEFT mode).
        * Leading whitespace is preserved as visual indentation.

        Args:
            text: Text to render (can include ``\\n`` for explicit line breaks)
            max_width / rel_max_width: Wrapping constraint
            x, y / rel_x, rel_y: Position (absolute or relative)
            style: TextStyle configuration
            max_y: Stop rendering past this y value
            auto_fit: Shrink font until text fits within *max_y*
            rel_max_y: *max_y* expressed as a screen-height fraction

        Returns:
            The y position after the last rendered line.
        """
        style = style or TextStyle()

        # --- auto-fit: shrink font until the text fits vertically ----------
        if auto_fit:
            style = self.auto_fit_font_size(
                text, style,
                max_width=max_width, rel_max_width=rel_max_width,
                start_y=y, rel_start_y=rel_y,
                max_y=max_y, rel_max_y=rel_max_y,
            )

        font = self._get_font(style.font_family, style.font_size, style.bold, style.italic)
        bold_font = self._get_font(style.font_family, style.font_size, bold=True, italic=style.italic)

        # Resolve positions
        pos_x = x if x is not None else (self.screen.abs_x(rel_x) if rel_x is not None else self.screen.abs_x(0.05))
        pos_y = y if y is not None else (self.screen.abs_y(rel_y) if rel_y is not None else self.screen.abs_y(0.05))

        # Resolve max_width
        if max_width is None:
            if rel_max_width is not None:
                max_width = self.screen.abs_x(rel_max_width)
            else:
                max_width = self.screen.abs_x(0.9)

        line_height = int(font.get_linesize() * style.line_spacing)

        # Split text by explicit newlines
        paragraphs = text.split('\n')
        current_y = pos_y
        has_bold = '**' in text  # fast path: skip rich parsing when not needed

        for paragraph in paragraphs:
            if not paragraph.strip():
                current_y += line_height
                continue

            # ---- per-paragraph metadata -----------
            content, force_center, indent_prefix = self._parse_line_meta(paragraph)
            indent_w = font.size(indent_prefix)[0] if indent_prefix else 0
            wrap_w = max(1, max_width - indent_w)

            # For wrapping, use the plain (no **) version of the text so
            # word boundaries are computed correctly.
            plain = self._strip_bold_markers(content)
            wrapped = self._wrap_text(plain, font, wrap_w)

            # If there is bold markup, we also need wrapped lines of the
            # *raw* content (with ** markers) so we can render segments.
            # Map plain-wrapped lines back to rich lines by re-splitting
            # the original content at the same word boundaries.
            if has_bold and '**' in content:
                rich_wrapped = self._wrap_text_preserving_markup(content, font, bold_font, wrap_w)
            else:
                rich_wrapped = wrapped

            for idx, plain_line in enumerate(wrapped):
                if max_y is not None and current_y > max_y:
                    return current_y

                if not plain_line.strip():
                    current_y += line_height
                    continue

                rich_line = rich_wrapped[idx] if idx < len(rich_wrapped) else plain_line

                # Determine alignment for this line
                if force_center:
                    align = TextAlign.CENTER
                else:
                    align = style.align

                # Measure the rendered width for alignment
                if has_bold and '**' in rich_line:
                    line_w = self._measure_rich_line_width(
                        rich_line, style.font_family, style.font_size, style.italic,
                    )
                else:
                    line_w = font.size(plain_line)[0]

                # Compute x
                if align == TextAlign.CENTER:
                    line_x = pos_x + (max_width - line_w) // 2
                elif align == TextAlign.RIGHT:
                    line_x = pos_x + max_width - line_w
                else:
                    line_x = pos_x + indent_w

                # Render
                if has_bold and '**' in rich_line:
                    self._render_rich_line(rich_line, line_x, current_y, style)
                else:
                    surf = font.render(plain_line, True, style.color.to_tuple())
                    self.screen.win.blit(surf, (line_x, current_y))

                current_y += line_height

        return current_y

    # ------------------------------------------------------------------
    def _wrap_text_preserving_markup(
        self,
        content: str,
        font: pg.font.Font,
        bold_font: pg.font.Font,
        max_width: int,
    ) -> list[str]:
        """Word-wrap *content* (which may contain ``**bold**`` markers)
        while keeping the markers intact in the output lines.

        Width measurement uses the appropriate font (bold vs normal)
        for each segment.
        """
        # Tokenise into words while keeping ** markers attached
        words = content.split()
        if not words:
            return ['']

        lines: list[str] = []
        current = words[0]

        def _seg_width(s: str) -> int:
            total = 0
            for seg, is_b in self._parse_rich_segments(s):
                f = bold_font if is_b else font
                total += f.size(seg)[0]
            return total

        for word in words[1:]:
            trial = f'{current} {word}'
            if _seg_width(trial) <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word

        lines.append(current)
        return lines
    
    def draw_text_block(
        self,
        lines: list[str] | str,
        x: int | None = None,
        y: int | None = None,
        rel_x: float | None = None,
        rel_y: float | None = None,
        style: TextStyle | None = None,
        line_spacing: int | None = None,
        max_width: int | None = None,
        auto_fit: bool = False,
        rel_max_y: float | None = None,
    ) -> int:
        """
        Draw multiple lines of text as a block.
        Empty strings create paragraph breaks.
        Accepts either a list of strings or a single string
        (which will be rendered via draw_paragraph).
        
        Args:
            lines: List of text lines (empty string = paragraph break), or a single string
            x, y: Absolute position
            rel_x, rel_y: Relative position
            style: TextStyle configuration
            line_spacing: Override style's line spacing
            max_width: Wrap lines to this width
            auto_fit: If True, reduce font size until text fits vertically
            rel_max_y: Maximum y as fraction of screen height (used with auto_fit)
        
        Returns:
            The y position after the last line
        """
        # If a plain string is passed, delegate to draw_paragraph
        if isinstance(lines, str):
            return self.draw_paragraph(
                lines,
                max_width=max_width,
                x=x, y=y,
                rel_x=rel_x, rel_y=rel_y,
                style=style,
                auto_fit=auto_fit,
                rel_max_y=rel_max_y,
            )
        style = style or TextStyle()
        font = self._get_font(style.font_family, style.font_size, style.bold, style.italic)
        
        pos_x = x if x is not None else (self.screen.abs_x(rel_x) if rel_x is not None else self.screen.abs_x(0.05))
        pos_y = y if y is not None else (self.screen.abs_y(rel_y) if rel_y is not None else self.screen.abs_y(0.05))
        
        if line_spacing is None:
            line_spacing = int(font.get_linesize() * style.line_spacing)
        
        current_y = pos_y
        
        for line in lines:
            if not line:  # Empty line = paragraph break
                current_y += line_spacing
                continue
            
            if max_width:
                # Wrap this line
                wrapped = self._wrap_text(line, font, max_width)
                for wline in wrapped:
                    if wline.strip():
                        current_y = self._render_aligned_line(
                            wline, font, style, pos_x, current_y, max_width
                        )
                    current_y += line_spacing
            else:
                current_y = self._render_aligned_line(
                    line, font, style, pos_x, current_y, self.screen.width - pos_x - 20
                )
                current_y += line_spacing
        
        return current_y
    
    def _render_aligned_line(
        self,
        text: str,
        font: pg.font.Font,
        style: TextStyle,
        x: int,
        y: int,
        width: int
    ) -> int:
        """Render a single line with alignment applied."""
        surface = font.render(text, True, style.color.to_tuple())
        
        if style.align == TextAlign.CENTER:
            line_x = x + (width - surface.get_width()) // 2
        elif style.align == TextAlign.RIGHT:
            line_x = x + width - surface.get_width()
        else:
            line_x = x
        
        self.screen.win.blit(surface, (line_x, y))
        return y
    
    def draw_centered_text(
        self,
        text: str,
        rel_y: float,
        style: TextStyle | None = None,
        max_width: int | None = None
    ) -> int:
        """
        Convenience method to draw horizontally centered wrapped text.
        
        Args:
            text: Text to render
            rel_y: Vertical position (0.0-1.0)
            style: TextStyle (align will be forced to CENTER)
            max_width: Wrapping width (default 92% of screen)
        
        Returns:
            Y position after last line
        """
        style = style or TextStyle()
        style.align = TextAlign.CENTER
        
        max_w = max_width or self.screen.abs_x(0.92)
        y_pos = self.screen.abs_y(rel_y)
        x_pos = (self.screen.width - max_w) // 2
        
        return self.draw_paragraph(text, max_width=max_w, x=x_pos, y=y_pos, style=style)


class TextInput:
    """
    Configurable text input system with support for:
    - Input mode restrictions (letters, numbers, alphanumeric, etc.)
    - Shift+key for special characters
    - Space handling
    - Custom validators
    - Placeholder text
    - Character limits
    
    Usage:
        screen = Screen(win)
        text_input = TextInput(
            screen,
            mode=InputMode.ALPHANUMERIC_SPACES,
            allow_shift_symbols=True,
            placeholder="Enter your name..."
        )
        
        # In your event loop:
        result = text_input.run(prompt="Subject Name:")
    """
    
    def __init__(
        self,
        screen: Screen,
        mode: InputMode = InputMode.ALPHANUMERIC_SPACES,
        allow_spaces: bool = True,
        allow_shift_symbols: bool = False,
        max_length: int | None = None,
        placeholder: str = "",
        custom_validator: Callable[[int], bool] | None = None,
        style: InputStyle | None = None
    ):
        self.screen = screen
        self.mode = mode
        self.allow_spaces = allow_spaces
        self.allow_shift_symbols = allow_shift_symbols
        self.max_length = max_length
        self.placeholder = placeholder
        self.custom_validator = custom_validator
        self.style = style or InputStyle()
        self.text_renderer = TextRenderer(screen)
        self.value = ""
        self.cursor_pos = 0  # cursor position within self.value
        self._cursor_blink_time = pg.time.get_ticks()  # reset on each keystroke
        self._cursor_blink_interval = 530  # ms per phase (visible / hidden)
    
    def is_valid_key(self, key: int, mods: int) -> tuple[bool, str]:
        """
        Check if a key press is valid and return the character to add.
        
        Returns:
            (is_valid, character_to_add)
        """
        shift_held = bool(mods & (pg.KMOD_SHIFT | pg.KMOD_CAPS))
        
        # Handle custom validator
        if self.mode == InputMode.CUSTOM and self.custom_validator:
            if self.custom_validator(key):
                char = chr(key)
                if shift_held and key in SHIFT_KEY_MAP and self.allow_shift_symbols:
                    return True, SHIFT_KEY_MAP[key]
                return True, char.upper() if shift_held else char.lower()
            return False, ""
        
        # Space handling
        if key == pg.K_SPACE:
            if self.allow_spaces and self.mode in (
                InputMode.ALPHANUMERIC_SPACES, InputMode.FULL_ASCII
            ):
                return True, " "
            return False, ""
        
        # Shift + number/symbol for special characters
        if shift_held and key in SHIFT_KEY_MAP:
            mapped = SHIFT_KEY_MAP[key]
            if self.mode == InputMode.FULL_ASCII:
                return True, mapped
            if self.allow_shift_symbols:
                return True, mapped
            # For EMAIL mode, allow shift-produced chars that are valid email chars
            if self.mode == InputMode.EMAIL and mapped in ('@', '.', '-', '_', '+'):
                return True, mapped
            return False, ""
        
        # Letters (a-z)
        if 97 <= key <= 122:  # lowercase
            if self.mode in (InputMode.LETTERS_ONLY, InputMode.ALPHANUMERIC,
                           InputMode.ALPHANUMERIC_SPACES, InputMode.EMAIL, InputMode.FULL_ASCII):
                char = chr(key)
                return True, char.upper() if shift_held else char
            return False, ""
        
        # Numbers (0-9)
        if 48 <= key <= 57:
            if self.mode in (InputMode.NUMBERS_ONLY, InputMode.ALPHANUMERIC,
                           InputMode.ALPHANUMERIC_SPACES, InputMode.EMAIL, InputMode.FULL_ASCII):
                return True, chr(key)
            return False, ""
        
        # Email special chars (direct key press, no shift)
        if self.mode == InputMode.EMAIL:
            if key in (ord('@'), ord('.'), ord('-'), ord('_'), ord('+')):
                return True, chr(key)
        
        # Full ASCII printable
        if self.mode == InputMode.FULL_ASCII:
            if 32 <= key <= 126:
                char = chr(key)
                if shift_held and 97 <= key <= 122:
                    return True, char.upper()
                return True, char
        
        return False, ""
    
    def handle_event(self, event: pg.event.Event) -> str | None:
        """
        Process a single pygame event.
        
        Returns:
            - None: continue input
            - "escape": user pressed escape (quit)
            - "submit": user pressed enter with valid input
            - "back": user pressed backspace on empty (optional navigation)
        """
        if event.type != pg.KEYDOWN:
            return None
        
        # Reset cursor blink so it's visible immediately after any keypress
        self._cursor_blink_time = pg.time.get_ticks()
        
        if event.key == pg.K_ESCAPE:
            return "escape"
        
        if event.key in (pg.K_RETURN, pg.K_KP_ENTER):
            if self.value:
                return "submit"
            return None
        
        if event.key in (pg.K_BACKSPACE, pg.K_DELETE):
            if self.cursor_pos > 0:
                self.value = self.value[:self.cursor_pos - 1] + self.value[self.cursor_pos:]
                self.cursor_pos -= 1
            return None
        
        # Left/right arrow key navigation
        if event.key == pg.K_LEFT:
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
            return None
        
        if event.key == pg.K_RIGHT:
            if self.cursor_pos < len(self.value):
                self.cursor_pos += 1
            return None
        
        # Home/End keys
        if event.key == pg.K_HOME:
            self.cursor_pos = 0
            return None
        
        if event.key == pg.K_END:
            self.cursor_pos = len(self.value)
            return None
        
        # Check length limit
        if self.max_length and len(self.value) >= self.max_length:
            return None
        
        # Validate and add character
        mods = pg.key.get_mods()
        is_valid, char = self.is_valid_key(event.key, mods)
        if is_valid and char:
            self.value = self.value[:self.cursor_pos] + char + self.value[self.cursor_pos:]
            self.cursor_pos += 1
        
        return None
    
    def draw(
        self,
        prompt: str = "",
        x: int | None = None,
        y: int | None = None,
        rel_x: float | None = None,
        rel_y: float | None = None,
        prompt_style: TextStyle | None = None
    ) -> None:
        """Draw the input field with prompt."""
        prompt_style = prompt_style or TextStyle(
            font_size=self.screen.scaled_font_size(20),
            align=TextAlign.LEFT
        )
        
        # Position
        pos_x = x if x is not None else (self.screen.abs_x(rel_x) if rel_x is not None else self.screen.abs_x(0.05))
        pos_y = y if y is not None else (self.screen.abs_y(rel_y) if rel_y is not None else self.screen.abs_y(0.4))
        
        # Draw prompt
        y_after = self.text_renderer.draw_paragraph(
            prompt,
            x=pos_x,
            y=pos_y,
            style=prompt_style,
            max_width=self.screen.abs_x(0.9)
        )
        
        # Draw input value or placeholder
        input_style = TextStyle(
            font_size=prompt_style.font_size,
            color=Colors.BLACK if self.value else Colors.GRAY
        )
        
        font = self.text_renderer._get_font(
            input_style.font_family, input_style.font_size,
            input_style.bold, input_style.italic
        )
        
        input_y = y_after + 10
        
        if self.value:
            # Draw text before cursor
            before_cursor = self.value[:self.cursor_pos]
            after_cursor = self.value[self.cursor_pos:]
            
            self.text_renderer.draw_text(before_cursor + after_cursor, x=pos_x, y=input_y, style=input_style)
            
            # Blinking vertical bar cursor
            elapsed = (pg.time.get_ticks() - self._cursor_blink_time) % (self._cursor_blink_interval * 2)
            if elapsed < self._cursor_blink_interval:
                cursor_x = pos_x + font.size(before_cursor)[0]
                cursor_top = input_y + 2
                cursor_bottom = input_y + font.get_height() - 2
                pg.draw.line(
                    self.screen.win,
                    input_style.color.to_tuple(),
                    (cursor_x, cursor_top),
                    (cursor_x, cursor_bottom),
                    2
                )
        else:
            # Draw placeholder
            self.text_renderer.draw_text(self.placeholder, x=pos_x, y=input_y, style=input_style)
            # Blinking vertical bar cursor at start
            elapsed = (pg.time.get_ticks() - self._cursor_blink_time) % (self._cursor_blink_interval * 2)
            if elapsed < self._cursor_blink_interval:
                cursor_top = input_y + 2
                cursor_bottom = input_y + font.get_height() - 2
                pg.draw.line(
                    self.screen.win,
                    Colors.BLACK.to_tuple(),
                    (pos_x, cursor_top),
                    (pos_x, cursor_bottom),
                    2
                )
    
    def run(
        self,
        prompt: str = "",
        additional_text: str = "",
        on_escape: str = "quit"
    ) -> str | None:
        """
        Run the input loop until user submits or cancels.
        
        Args:
            prompt: Text displayed above input
            additional_text: Extra context text
            on_escape: "quit" to exit app, "return" to return None
        
        Returns:
            The entered text, or None if cancelled
        """
        self.value = ""
        self.cursor_pos = 0
        self._cursor_blink_time = pg.time.get_ticks()
        
        while True:
            for event in pg.event.get():
                result = self.handle_event(event)
                
                if result == "escape":
                    if on_escape == "quit":
                        self.screen.handle_escape()
                    return None
                
                if result == "submit":
                    return self.value
            
            # Draw
            self.screen.fill()
            pg.mouse.set_visible(False)
            
            full_prompt = f"{additional_text}\n\n{prompt}" if additional_text else prompt
            self.draw(prompt=full_prompt, rel_y=0.05)
            
            self.screen.update()


class Button:
    """
    Flexible button class with multiple states and styles.
    
    Usage:
        button = Button(
            screen=screen,
            text="Click Me",
            rel_x=0.5, rel_y=0.5,
            rel_width=0.2, rel_height=0.08,
            style=ButtonStyle(bg_color=Colors.GREEN)
        )
        
        # In render loop:
        button.draw()
        if button.is_clicked(mouse_pos, clicked):
            handle_click()
    """
    
    def __init__(
        self,
        screen: Screen,
        text: str,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
        rel_x: float | None = None,
        rel_y: float | None = None,
        rel_width: float | None = None,
        rel_height: float | None = None,
        style: ButtonStyle | None = None,
        enabled: bool = True,
        center_anchor: bool = True,
        on_click: Callable[[], Any] | None = None
    ):
        self.screen = screen
        self.text = text
        self.style = style or ButtonStyle()
        self.enabled = enabled
        self.center_anchor = center_anchor
        self.on_click = on_click
        self.state = ButtonState.NORMAL
        self.selected = False  # Persistent selection state
        
        # Calculate dimensions
        w = width if width is not None else (
            screen.abs_x(rel_width) if rel_width is not None else screen.abs_x(0.15)
        )
        h = height if height is not None else (
            screen.abs_y(rel_height) if rel_height is not None else screen.abs_y(0.07)
        )
        
        # Calculate position
        px = x if x is not None else (
            screen.abs_x(rel_x) if rel_x is not None else 0
        )
        py = y if y is not None else (
            screen.abs_y(rel_y) if rel_y is not None else 0
        )
        
        # Adjust for center anchor
        if center_anchor:
            px -= w // 2
            py -= h // 2
        
        self.rect = pg.Rect(px, py, w, h)
        self._font_cache: dict = {}
    
    def update_position(
        self,
        x: int | None = None,
        y: int | None = None,
        rel_x: float | None = None,
        rel_y: float | None = None
    ) -> None:
        """Update button position."""
        px = x if x is not None else (
            self.screen.abs_x(rel_x) if rel_x is not None else self.rect.x
        )
        py = y if y is not None else (
            self.screen.abs_y(rel_y) if rel_y is not None else self.rect.y
        )
        
        if self.center_anchor:
            px -= self.rect.width // 2
            py -= self.rect.height // 2
        
        self.rect.x = px
        self.rect.y = py
    
    def _get_current_colors(self) -> tuple[Color, Color]:
        """Get background and text colors based on current state."""
        if not self.enabled:
            return self.style.disabled_bg_color, self.style.disabled_text_color
        
        bg = self.style.bg_color
        # Apply selection darkening (persistent) - no hover when selected
        if self.selected:
            bg = bg.darken(self.style.selected_darken)
            # Selected buttons don't get hover effect
        else:
            # Only apply hover/pressed to non-selected buttons
            if self.state == ButtonState.HOVERED:
                bg = bg.darken(self.style.hover_darken)
            elif self.state == ButtonState.PRESSED:
                bg = bg.darken(self.style.pressed_darken)
        
        return bg, self.style.text_color
    
    def draw(self) -> None:
        """Draw the button."""
        bg_color, text_color = self._get_current_colors()
        
        # Draw background
        pg.draw.rect(self.screen.win, bg_color.to_tuple(), self.rect)
        
        # Draw border
        if self.style.border_width > 0:
            pg.draw.rect(
                self.screen.win,
                self.style.border_color.to_tuple(),
                self.rect,
                self.style.border_width
            )
        
        # Draw text (with bold support)
        font_size = self.style.font_size or max(14, self.screen.height // 44)
        
        if '**' in self.text:
            # Rich text with bold support
            self._draw_rich_text(font_size, text_color)
        else:
            # Simple text rendering
            font = pg.font.SysFont(self.style.font_family, font_size)
            text_surface = font.render(self.text, True, text_color.to_tuple())
            text_rect = text_surface.get_rect(center=self.rect.center)
            self.screen.win.blit(text_surface, text_rect)
    
    def _draw_rich_text(self, font_size: int, text_color: Color) -> None:
        """Draw button text with **bold** markup support."""
        import re
        BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
        
        # Parse segments
        segments: list[tuple[str, bool]] = []
        last = 0
        for m in BOLD_RE.finditer(self.text):
            if m.start() > last:
                segments.append((self.text[last:m.start()], False))
            segments.append((m.group(1), True))
            last = m.end()
        if last < len(self.text):
            segments.append((self.text[last:], False))
        if not segments:
            segments = [(self.text, False)]
        
        # Measure total width
        total_width = 0
        surfaces: list[tuple[pg.Surface, bool]] = []
        for text, is_bold in segments:
            font = pg.font.SysFont(self.style.font_family, font_size, bold=is_bold)
            surf = font.render(text, True, text_color.to_tuple())
            surfaces.append((surf, is_bold))
            total_width += surf.get_width()
        
        # Center and draw
        x = self.rect.centerx - total_width // 2
        y = self.rect.centery
        for surf, _ in surfaces:
            rect = surf.get_rect(midleft=(x, y))
            self.screen.win.blit(surf, rect)
            x += surf.get_width()
    
    def contains_point(self, pos: tuple[int, int]) -> bool:
        """Check if a point is within the button."""
        return self.rect.collidepoint(pos)
    
    def update_state(self, mouse_pos: tuple[int, int], mouse_pressed: bool = False) -> None:
        """Update button state based on mouse position and click state."""
        if not self.enabled:
            self.state = ButtonState.DISABLED
            return
        
        if self.contains_point(mouse_pos):
            self.state = ButtonState.PRESSED if mouse_pressed else ButtonState.HOVERED
        else:
            self.state = ButtonState.NORMAL
    
    def is_clicked(self, mouse_pos: tuple[int, int], was_clicked: bool) -> bool:
        """
        Check if button was clicked.
        
        Args:
            mouse_pos: Current mouse position
            was_clicked: True if mouse button was just released
        
        Returns:
            True if this button was clicked
        """
        if not self.enabled:
            return False
        
        if was_clicked and self.contains_point(mouse_pos):
            if self.on_click:
                self.on_click()
            return True
        return False


class GridLayout:
    """
    Layout helper for arranging items in a grid.
    
    Useful for creating grids of buttons, images, or other elements.
    
    Usage:
        layout = GridLayout(
            screen=screen,
            cols=3,
            rel_x_start=0.1, rel_x_end=0.9,
            rel_y_start=0.2, rel_y_end=0.6

        )
        
        for i, rect in enumerate(layout.get_rects(item_count=9)):
            # Use rect to position items
    """
    
    def __init__(
        self,
        screen: Screen,
        cols: int = 3,
        x_start: int | None = None,
        x_end: int | None = None,
        y_start: int | None = None,
        y_end: int | None = None,
        rel_x_start: float | None = None,
        rel_x_end: float | None = None,
        rel_y_start: float | None = None,
        rel_y_end: float | None = None,
        spacing: int = 10,
        item_height: int | None = None,
        rel_item_height: float | None = None
    ):
        self.screen = screen
        self.cols = max(1, cols)
        self.spacing = spacing
        
        # Calculate bounds
        self.x_start = x_start if x_start is not None else (
            screen.abs_x(rel_x_start) if rel_x_start is not None else screen.abs_x(0.06)
        )
        self.x_end = x_end if x_end is not None else (
            screen.abs_x(rel_x_end) if rel_x_end is not None else screen.abs_x(0.94)
        )
        self.y_start = y_start if y_start is not None else (
            screen.abs_y(rel_y_start) if rel_y_start is not None else screen.abs_y(0.2)
        )
        self.y_end = y_end if y_end is not None else (
            screen.abs_y(rel_y_end) if rel_y_end is not None else screen.abs_y(0.8)
        )
        
        # Item height
        self.item_height = item_height if item_height is not None else (
            screen.abs_y(rel_item_height) if rel_item_height is not None else max(36, screen.abs_y(0.07))
        )
    
    def get_rects(self, item_count: int) -> list[pg.Rect]:
        """Calculate rectangles for all items in the grid."""
        if item_count <= 0:
            return []
        
        rows = (item_count + self.cols - 1) // self.cols
        
        available_w = self.x_end - self.x_start
        available_h = self.y_end - self.y_start
        
        # Calculate item width
        total_spacing_x = (self.cols - 1) * self.spacing
        item_width = (available_w - total_spacing_x) // self.cols
        
        # Calculate row spacing
        row_gap = self.spacing
        total_height = rows * self.item_height + (rows - 1) * row_gap
        
        # Center vertically if space permits
        y_offset = (available_h - total_height) // 2 if total_height < available_h else 0
        
        rects = []
        for idx in range(item_count):
            row = idx // self.cols
            col = idx % self.cols
            
            x = self.x_start + col * (item_width + self.spacing)
            y = self.y_start + y_offset + row * (self.item_height + row_gap)
            
            rects.append(pg.Rect(x, y, item_width, self.item_height))
        
        return rects


class ScreenBuilder:
    """
    High-level screen composition utility.
    
    Combines Screen, TextRenderer, buttons, and layouts into
    convenient methods for building common screen types.
    
    Usage:
        builder = ScreenBuilder(win)
        
        # Simple message screen
        builder.message_screen(
            "Welcome!",
            "Press SPACE to continue",
            wait_key=pg.K_SPACE
        )
        
        # Input screen
        name = builder.input_screen(
            "Enter your name:",
            mode=InputMode.LETTERS_ONLY
        )
    """
    
    def __init__(self, win: pg.Surface, background_color: Color = Colors.BACKGROUND):
        self.screen = Screen(win, background_color)
        self.text_renderer = TextRenderer(self.screen)
    
    def message_screen(
        self,
        text: str,
        title: str | None = None,
        title_style: TextStyle | None = None,
        body_style: TextStyle | None = None,
        wait_key: int | None = pg.K_SPACE,
        continue_text: str | None = None,
        timeout_ms: int | None = None
    ) -> None:
        """
        Display a message screen and wait for key press.
        
        Args:
            text: Main body text
            title: Optional title text
            title_style: Style for title
            body_style: Style for body
            wait_key: Key to wait for (None = don't wait)
            continue_text: Optional "press X to continue" text
            timeout_ms: Auto-continue after this many ms
        """
        # Default styles
        if title_style is None:
            title_style = TextStyle(
                font_size=self.screen.scaled_font_size(10),
                bold=True,
                align=TextAlign.CENTER
            )
        
        if body_style is None:
            body_style = TextStyle(
                font_size=self.screen.scaled_font_size(20),
                align=TextAlign.LEFT
            )
        
        start_time = pg.time.get_ticks()
        
        while True:
            self.screen.fill()
            pg.mouse.set_visible(False)
            
            y_pos = self.screen.abs_y(0.05)
            
            # Draw title
            if title:
                y_pos = self.text_renderer.draw_centered_text(
                    title, rel_y=0.05, style=title_style, max_width=self.screen.abs_x(0.9)
                )
                y_pos += self.screen.abs_y(0.05)
            
            # Draw body
            self.text_renderer.draw_paragraph(
                text,
                x=self.screen.abs_x(0.05),
                y=y_pos,
                style=body_style,
                max_width=self.screen.abs_x(0.9)
            )
            
            # Draw continue hint
            if continue_text:
                hint_style = TextStyle(
                    font_size=self.screen.scaled_font_size(30),
                    color=Colors.DARK_GRAY,
                    italic=True,
                    align=TextAlign.CENTER
                )
                self.text_renderer.draw_centered_text(
                    continue_text,
                    rel_y=0.92,
                    style=hint_style
                )
            
            self.screen.update()
            
            # Check timeout
            if timeout_ms and (pg.time.get_ticks() - start_time) >= timeout_ms:
                return
            
            # Handle events
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        self.screen.handle_escape()
                    if wait_key and event.key == wait_key:
                        return
            
            if wait_key is None:
                return
    
    def input_screen(
        self,
        prompt: str,
        mode: InputMode = InputMode.ALPHANUMERIC_SPACES,
        allow_shift_symbols: bool = False,
        placeholder: str = "",
        max_length: int | None = None,
        header: str | None = None
    ) -> str | None:
        """
        Display an input screen and return the entered text.
        
        Args:
            prompt: Input prompt text
            mode: Input restrictions
            allow_shift_symbols: Allow shift+number symbols
            placeholder: Placeholder text
            max_length: Maximum input length
            header: Optional header text
        
        Returns:
            Entered text or None if cancelled
        """
        text_input = TextInput(
            screen=self.screen,
            mode=mode,
            allow_shift_symbols=allow_shift_symbols,
            placeholder=placeholder,
            max_length=max_length,
            allow_spaces=(mode in (InputMode.ALPHANUMERIC_SPACES, InputMode.FULL_ASCII))
        )
        
        full_prompt = f"{header}\n\n{prompt}" if header else prompt
        return text_input.run(prompt=full_prompt)
    
    def choice_screen(
        self,
        question: str,
        options: list[str],
        title: str | None = None,
        allow_back: bool = False
    ) -> str | None:
        """
        Display a multiple choice screen.
        
        Args:
            question: Question text
            options: List of choice options
            title: Optional title
            allow_back: Allow returning None to go back
        
        Returns:
            Selected option text, or None if back
        """
        buttons: list[Button] = []
        
        # Create option buttons
        y_start = 0.35
        for i, option in enumerate(options):
            btn = Button(
                screen=self.screen,
                text=option,
                rel_x=0.5,
                rel_y=y_start + i * 0.12,
                rel_width=0.7,
                rel_height=0.08,
                style=ButtonStyle(bg_color=Colors.WHITE, text_color=Colors.BLACK)
            )
            buttons.append(btn)
        
        selected: str | None = None
        
        while selected is None:
            self.screen.fill()
            pg.mouse.set_visible(True)
            
            # Draw title
            y_pos = self.screen.abs_y(0.05)
            if title:
                title_style = TextStyle(
                    font_size=self.screen.scaled_font_size(12),
                    bold=True,
                    align=TextAlign.CENTER
                )
                y_pos = self.text_renderer.draw_centered_text(
                    title, rel_y=0.05, style=title_style
                )
            
            # Draw question
            q_style = TextStyle(
                font_size=self.screen.scaled_font_size(20),
                align=TextAlign.CENTER
            )
            self.text_renderer.draw_centered_text(
                question, rel_y=0.18, style=q_style, max_width=self.screen.abs_x(0.85)
            )
            
            # Draw buttons
            mouse_pos = pg.mouse.get_pos()
            for btn in buttons:
                btn.update_state(mouse_pos)
                btn.draw()
            
            self.screen.update()
            
            # Handle events
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        if allow_back:
                            return None
                        self.screen.handle_escape()
                
                elif event.type == pg.MOUSEBUTTONUP:
                    for btn in buttons:
                        if btn.is_clicked(mouse_pos, True):
                            selected = btn.text
                            break
        
        return selected
    
    def button_screen(
        self,
        instructions: list[str],
        buttons_config: list[dict],
        header: str | None = None,
        on_button_click: Callable[[str], bool] | None = None
    ) -> str | None:
        """
        Display a screen with multiple buttons.
        
        Args:
            instructions: List of instruction lines
            buttons_config: List of button configs, each dict has:
                - text: button text
                - rel_x, rel_y: position
                - style: ButtonStyle (optional)
                - enabled: bool (optional)
            header: Optional header
            on_button_click: Callback(button_text) -> should_exit
        
        Returns:
            Text of clicked button that caused exit
        """
        buttons: list[Button] = []
        
        for cfg in buttons_config:
            btn = Button(
                screen=self.screen,
                text=cfg['text'],
                rel_x=cfg.get('rel_x', 0.5),
                rel_y=cfg.get('rel_y', 0.5),
                rel_width=cfg.get('rel_width', 0.2),
                rel_height=cfg.get('rel_height', 0.08),
                style=cfg.get('style', ButtonStyle()),
                enabled=cfg.get('enabled', True)
            )
            buttons.append(btn)
        
        while True:
            self.screen.fill()
            pg.mouse.set_visible(True)
            
            # Draw header
            y_pos = self.screen.abs_y(0.05)
            if header:
                header_style = TextStyle(
                    font_size=self.screen.scaled_font_size(14),
                    bold=True,
                    align=TextAlign.CENTER
                )
                y_pos = self.text_renderer.draw_centered_text(
                    header, rel_y=0.05, style=header_style
                )
                y_pos += self.screen.abs_y(0.03)
            
            # Draw instructions
            inst_style = TextStyle(
                font_size=self.screen.scaled_font_size(28),
                align=TextAlign.CENTER
            )
            for line in instructions:
                if line:
                    y_pos = self.text_renderer.draw_centered_text(
                        line, rel_y=self.screen.rel_y(y_pos),
                        style=inst_style, max_width=self.screen.abs_x(0.9)
                    )
                else:
                    y_pos += self.screen.scaled_font_size(28)
            
            # Draw buttons
            mouse_pos = pg.mouse.get_pos()
            for btn in buttons:
                btn.update_state(mouse_pos)
                btn.draw()
            
            self.screen.update()
            
            # Handle events
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        self.screen.handle_escape()
                
                elif event.type == pg.MOUSEBUTTONUP:
                    for btn in buttons:
                        if btn.is_clicked(mouse_pos, True):
                            if on_button_click:
                                if on_button_click(btn.text):
                                    return btn.text
                            else:
                                return btn.text


def wait_for_key(key: int) -> None:
    """
    Block until a specific key is pressed.
    
    Handles escape to quit cleanly.
    """
    while True:
        for event in pg.event.get():
            if event.type == pg.KEYDOWN:
                if event.key == key:
                    return
                elif event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_screen(win: pg.Surface, bg_color: Color = Colors.BACKGROUND) -> Screen:
    """Create a Screen instance."""
    return Screen(win, bg_color)


def create_text_renderer(screen: Screen) -> TextRenderer:
    """Create a TextRenderer for the given screen."""
    return TextRenderer(screen)


def create_button(
    screen: Screen,
    text: str,
    rel_x: float = 0.5,
    rel_y: float = 0.5,
    rel_width: float = 0.15,
    rel_height: float = 0.07,
    style: ButtonStyle | None = None,
    enabled: bool = True
) -> Button:
    """Create a button with sensible defaults."""
    return Button(
        screen=screen,
        text=text,
        rel_x=rel_x,
        rel_y=rel_y,
        rel_width=rel_width,
        rel_height=rel_height,
        style=style or ButtonStyle(),
        enabled=enabled
    )


def show_message(
    win: pg.Surface,
    text: str,
    wait_key: int = pg.K_SPACE,
    title: str | None = None
) -> None:
    """Quick utility to show a message screen."""
    builder = ScreenBuilder(win)
    builder.message_screen(text, title=title, wait_key=wait_key)


def get_text_input(
    win: pg.Surface,
    prompt: str,
    mode: InputMode = InputMode.ALPHANUMERIC_SPACES
) -> str | None:
    """Quick utility to get text input."""
    builder = ScreenBuilder(win)
    return builder.input_screen(prompt, mode=mode)


# =============================================================================
# QUESTIONNAIRE & ADVANCED COMPONENTS
# =============================================================================

@dataclass
class CheckboxStyle:
    """Style configuration for checkbox/radio options."""
    box_color_unchecked: Color = field(default_factory=lambda: Colors.WHITE)
    box_color_checked: Color = field(default_factory=lambda: Colors.RED)
    border_color: Color = field(default_factory=lambda: Colors.BLACK)
    border_width: int = 2
    text_color: Color = field(default_factory=lambda: Colors.BLACK)
    font_family: str = DEFAULT_FONT_FAMILY
    font_size: int | None = None  # None = auto-scale
    box_size: int | None = None   # None = auto-scale based on font


class CheckboxOption:
    """
    A single checkbox/radio option for questionnaires.
    
    Can be used standalone or as part of a RadioButtonGroup.
    
    Usage:
        option = CheckboxOption(
            screen=screen,
            text="Option A",
            x=100, y=200
        )
        option.draw()
        if option.is_clicked(mouse_pos, clicked):
            option.toggle()
    """
    
    def __init__(
        self,
        screen: Screen,
        text: str,
        x: int | None = None,
        y: int | None = None,
        rel_x: float | None = None,
        rel_y: float | None = None,
        style: CheckboxStyle | None = None,
        checked: bool = False,
        value: Any = None
    ):
        self.screen = screen
        self.text = text
        self.style = style or CheckboxStyle()
        self.checked = checked
        self.value = value if value is not None else text
        
        # Calculate font size
        self.font_size = self.style.font_size or max(14, screen.height // 20)
        
        # Calculate box size
        self.box_size = self.style.box_size or max(self.font_size, int(0.015 * min(screen.width, screen.height)))
        
        # Position
        self.x = x if x is not None else (screen.abs_x(rel_x) if rel_x is not None else screen.abs_x(0.05))
        self.y = y if y is not None else (screen.abs_y(rel_y) if rel_y is not None else screen.abs_y(0.5))
        
        self.rect = pg.Rect(self.x, self.y, self.box_size, self.box_size)
        self.text_x = self.x + int(1.5 * self.box_size)
        self.text_y = self.y - int(0.1 * self.box_size)
    
    def draw(self) -> None:
        """Draw the checkbox and its label."""
        # Draw box
        box_color = self.style.box_color_checked if self.checked else self.style.box_color_unchecked
        pg.draw.rect(self.screen.win, box_color.to_tuple(), self.rect)
        pg.draw.rect(self.screen.win, self.style.border_color.to_tuple(), self.rect, self.style.border_width)
        
        # Draw text
        font = pg.font.SysFont(self.style.font_family, self.font_size)
        text_surface = font.render(self.text, True, self.style.text_color.to_tuple())
        self.screen.win.blit(text_surface, (self.text_x, self.text_y))
    
    def contains_point(self, pos: tuple[int, int]) -> bool:
        """Check if point is within the checkbox."""
        return self.rect.collidepoint(pos)
    
    def toggle(self) -> None:
        """Toggle checked state."""
        self.checked = not self.checked
    
    def select(self) -> None:
        """Set to checked."""
        self.checked = True
    
    def deselect(self) -> None:
        """Set to unchecked."""
        self.checked = False
    
    def is_clicked(self, mouse_pos: tuple[int, int], was_clicked: bool) -> bool:
        """Check if checkbox was clicked."""
        return was_clicked and self.contains_point(mouse_pos)


class RadioButtonGroup:
    """
    A group of mutually exclusive radio button options.
    
    Only one option can be selected at a time (single-select).
    Matches the behavior of your existing questionnaire buttons.
    
    Usage:
        group = RadioButtonGroup(
            screen=screen,
            options=["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"],
            question_y=200,
            style=CheckboxStyle()
        )
        
        # In render loop:
        group.draw()
        group.handle_click(mouse_pos, was_clicked)
        
        # Get selected value:
        selected = group.get_selected()
    """
    
    def __init__(
        self,
        screen: Screen,
        options: list[str],
        question_y: int,
        x_start: float = 0.05,
        style: CheckboxStyle | None = None,
        max_cols: int = 1,
        spacing_scalar: float = 1.5,
        values: list[Any] | None = None
    ):
        self.screen = screen
        self.style = style or CheckboxStyle()
        self.options: list[CheckboxOption] = []
        self._selected_index: int | None = None
        
        # Calculate positioning
        font_size = self.style.font_size or max(14, screen.height // 20)
        buffer = screen.height // 20
        row_spacing = int(spacing_scalar * font_size)
        
        # Calculate available space
        max_y = int(0.85 * screen.height) - font_size
        y_start = question_y + buffer
        
        # Determine number of columns needed
        available_height = max(1, max_y - y_start)
        max_rows_one_col = max(1, available_height // row_spacing)
        n_cols = 1 if len(options) <= max_rows_one_col else min(max_cols, 2)
        
        rows_per_col = (len(options) + n_cols - 1) // n_cols
        
        # Column x positions
        x_left = int(x_start * screen.width)
        x_right = int((x_start + 0.45) * screen.width)
        
        # Create option checkboxes
        left_count = len(options) if n_cols == 1 else (len(options) + 1) // 2
        
        for idx, opt_text in enumerate(options):
            if n_cols == 1 or idx < left_count:
                col = 0
                row = idx
            else:
                col = 1
                row = idx - left_count
            
            x = x_left if col == 0 else x_right
            y = y_start + row * row_spacing
            
            opt_value = values[idx] if values and idx < len(values) else opt_text
            
            checkbox = CheckboxOption(
                screen=screen,
                text=opt_text,
                x=x,
                y=y,
                style=self.style,
                value=opt_value
            )
            self.options.append(checkbox)
    
    def draw(self) -> None:
        """Draw all options."""
        for option in self.options:
            option.draw()
    
    def handle_click(self, mouse_pos: tuple[int, int], was_clicked: bool) -> bool:
        """
        Handle click events. Returns True if an option was clicked.
        Automatically deselects other options (single-select behavior).
        """
        if not was_clicked:
            return False
        
        for idx, option in enumerate(self.options):
            if option.contains_point(mouse_pos):
                # Deselect all others
                for other_idx, other in enumerate(self.options):
                    if other_idx != idx:
                        other.deselect()
                
                # Toggle this one (or just select it)
                option.select()
                self._selected_index = idx
                return True
        
        return False
    
    def get_selected(self) -> Any | None:
        """Get the value of the selected option, or None if nothing selected."""
        for option in self.options:
            if option.checked:
                return option.value
        return None
    
    def get_selected_index(self) -> int | None:
        """Get the index of the selected option."""
        for idx, option in enumerate(self.options):
            if option.checked:
                return idx
        return None
    
    def has_selection(self) -> bool:
        """Check if any option is selected."""
        return any(opt.checked for opt in self.options)
    
    def clear_selection(self) -> None:
        """Clear all selections."""
        for option in self.options:
            option.deselect()
        self._selected_index = None


class SubmitButton:
    """
    A submit button for questionnaires.
    
    Only activates when a condition is met (e.g., an option is selected).
    
    Usage:
        submit = SubmitButton(screen, "Submit")
        submit.draw(enabled=group.has_selection())
        if submit.is_clicked(mouse_pos, clicked) and group.has_selection():
            return group.get_selected()
    """
    
    def __init__(
        self,
        screen: Screen,
        text: str = "Submit",
        rel_x: float = 0.5,
        rel_y: float = 0.85,
        style: ButtonStyle | None = None
    ):
        self.screen = screen
        self.text = text
        
        # Default style for submit button (white bg, black text)
        if style is None:
            style = ButtonStyle(
                bg_color=Colors.WHITE,
                text_color=Colors.BLACK,
                border_width=3
            )
        self.style = style
        
        # Calculate size
        font_size = max(14, int(0.85 * (screen.height // 20)))
        font = pg.font.SysFont(self.style.font_family, font_size)
        text_surface = font.render(text, True, Colors.BLACK.to_tuple())
        text_w, text_h = text_surface.get_size()
        
        padding_x = int(0.02 * screen.width)
        padding_y = int(0.01 * screen.height)
        
        width = max(text_w + 2 * padding_x, int(0.08 * screen.width))
        height = max(text_h + 2 * padding_y, int(0.04 * screen.height))
        
        x = screen.abs_x(rel_x) - width // 2
        y = screen.abs_y(rel_y)
        
        self.rect = pg.Rect(x, y, width, height)
        self.font_size = font_size
    
    def draw(self, enabled: bool = True) -> None:
        """Draw the submit button."""
        if enabled:
            bg_color = self.style.bg_color
            text_color = self.style.text_color
        else:
            bg_color = Colors.GRAY
            text_color = Colors.DARK_GRAY
        
        pg.draw.rect(self.screen.win, bg_color.to_tuple(), self.rect)
        pg.draw.rect(self.screen.win, self.style.border_color.to_tuple(), self.rect, self.style.border_width)
        
        font = pg.font.SysFont(self.style.font_family, self.font_size)
        text_surface = font.render(self.text, True, text_color.to_tuple())
        text_rect = text_surface.get_rect(center=self.rect.center)
        self.screen.win.blit(text_surface, text_rect)
    
    def contains_point(self, pos: tuple[int, int]) -> bool:
        """Check if point is within the button."""
        return self.rect.collidepoint(pos)
    
    def is_clicked(self, mouse_pos: tuple[int, int], was_clicked: bool) -> bool:
        """Check if button was clicked."""
        return was_clicked and self.contains_point(mouse_pos)


class PagedScreen:
    """
    Multi-page screen with arrow key navigation.
    
    Perfect for consent forms and multi-page instructions.
    
    Usage:
        pages = [
            "Page 1: Study Information...",
            "Page 2: Risks and Benefits...",
            "Page 3: Confidentiality...",
        ]
        
        paged = PagedScreen(screen, pages)
        final_page = paged.run()  # Returns page index when user proceeds past last page
    """
    
    def __init__(
        self,
        screen: Screen,
        pages: list[str],
        allow_back: bool = True,
        show_progress: bool = True,
        navigation_hint: str = "Use arrow keys to navigate",
        text_renderer: TextRenderer | None = None
    ):
        self.screen = screen
        self.pages = pages
        self.allow_back = allow_back
        self.show_progress = show_progress
        self.navigation_hint = navigation_hint
        self.text_renderer = text_renderer or TextRenderer(screen)
        self.current_page = 0
    
    def draw_page(self, page_index: int) -> None:
        """Draw a single page."""
        self.screen.fill()
        pg.mouse.set_visible(False)
        
        # Draw page content
        style = TextStyle(
            font_size=self.screen.scaled_font_size(20),
            align=TextAlign.LEFT
        )
        
        self.text_renderer.draw_paragraph(
            self.pages[page_index],
            rel_x=0.05,
            rel_y=0.05,
            style=style,
            max_width=self.screen.abs_x(0.9)
        )
        
        # Draw progress indicator
        if self.show_progress:
            progress_style = TextStyle(
                font_size=self.screen.scaled_font_size(40),
                color=Colors.DARK_GRAY,
                align=TextAlign.CENTER
            )
            progress_text = f"Page {page_index + 1} of {len(self.pages)}"
            self.text_renderer.draw_centered_text(
                progress_text, rel_y=0.95, style=progress_style
            )
        
        self.screen.update()
    
    def run(self) -> int:
        """
        Run the paged screen navigation.
        
        Returns:
            The page index when user proceeds past the last page
        """
        self.current_page = 0
        
        while True:
            self.draw_page(self.current_page)
            
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        self.screen.handle_escape()
                    
                    elif event.key == pg.K_RIGHT:
                        if self.current_page < len(self.pages) - 1:
                            self.current_page += 1
                        else:
                            # Past last page - exit
                            return self.current_page
                    
                    elif event.key == pg.K_LEFT and self.allow_back:
                        if self.current_page > 0:
                            self.current_page -= 1
                    
                    elif event.key == pg.K_SPACE:
                        # Space also advances
                        if self.current_page < len(self.pages) - 1:
                            self.current_page += 1
                        else:
                            return self.current_page


class AudioTimer:
    """
    Helper class for tracking audio playback timing.
    
    Handles cooldown periods after audio playback to prevent
    button clicks during audio.
    
    Usage:
        timer = AudioTimer()
        
        # When audio starts:
        timer.start(duration_ms)
        
        # Check if can interact:
        if timer.can_interact():
            # Handle clicks
        
        # Check if audio still playing:
        if timer.is_playing():
            # Show "playing" indicator
    """
    
    def __init__(self, cooldown_ms: int = 250):
        self.cooldown_ms = cooldown_ms
        self._start_time: int = 0
        self._duration: int = 0
    
    def start(self, duration_ms: int) -> None:
        """Mark audio as started with given duration."""
        self._start_time = pg.time.get_ticks()
        self._duration = duration_ms
    
    def reset(self) -> None:
        """Reset the timer."""
        self._start_time = 0
        self._duration = 0
    
    def elapsed(self) -> int:
        """Get milliseconds since audio started."""
        if self._start_time == 0:
            return 0
        return pg.time.get_ticks() - self._start_time
    
    def is_playing(self) -> bool:
        """Check if audio is still playing."""
        if self._start_time == 0:
            return False
        return self.elapsed() < self._duration
    
    def can_interact(self) -> bool:
        """Check if enough time has passed to allow interaction."""
        if self._start_time == 0:
            return True
        return self.elapsed() >= self._duration + self.cooldown_ms
    
    @property
    def duration(self) -> int:
        """Get the duration of the current/last audio."""
        return self._duration


class AudioButton(Button):
    """
    A button with built-in audio playback timing support.
    
    Automatically handles dimming during playback and cooldown.
    
    Usage:
        btn = AudioButton(screen, "Play Audio", rel_x=0.5, rel_y=0.5)
        
        # In render loop:
        btn.draw(timer)  # Pass AudioTimer
        
        if btn.is_clickable(timer) and btn.is_clicked(mouse_pos, clicked):
            duration = audio_engine.play(pcm_data)
            timer.start(duration)
    """
    
    def __init__(
        self,
        screen: Screen,
        text: str,
        x: int | None = None,
        y: int | None = None,
        rel_x: float | None = None,
        rel_y: float | None = None,
        rel_width: float = 0.18,
        rel_height: float = 0.08,
        style: ButtonStyle | None = None,
        enabled: bool = True,
        max_plays: int | None = None,
        playing_text: str | None = None
    ):
        super().__init__(
            screen=screen,
            text=text,
            x=x, y=y,
            rel_x=rel_x, rel_y=rel_y,
            rel_width=rel_width, rel_height=rel_height,
            style=style or ButtonStyle(bg_color=Colors.BLUE, text_color=Colors.WHITE),
            enabled=enabled
        )
        self.max_plays = max_plays
        self.play_count = 0
        self.base_text = text
        self.playing_text = playing_text or text
    
    def is_clickable(self, timer: AudioTimer) -> bool:
        """Check if button can be clicked (respects timing and play limits)."""
        if not self.enabled:
            return False
        if self.max_plays is not None and self.play_count >= self.max_plays:
            return False
        return timer.can_interact()
    
    def draw_with_timer(self, timer: AudioTimer) -> None:
        """Draw button with timer-aware state."""
        is_playing = timer.is_playing()
        can_click = self.is_clickable(timer)
        
        # Determine colors
        if self.max_plays is not None and self.play_count >= self.max_plays:
            bg_color = Colors.GRAY
            text_color = Colors.BLACK
            display_text = "Max Plays Reached"
        elif is_playing:
            bg_color = self.style.bg_color.darken(0.6)
            text_color = Colors.GRAY
            display_text = self.playing_text
        elif not can_click:
            bg_color = self.style.bg_color.darken(0.5)
            text_color = Colors.GRAY
            display_text = self.base_text
        else:
            bg_color = self.style.bg_color
            text_color = self.style.text_color
            display_text = self.base_text
        
        # Draw
        pg.draw.rect(self.screen.win, bg_color.to_tuple(), self.rect)
        pg.draw.rect(self.screen.win, self.style.border_color.to_tuple(), self.rect, self.style.border_width)
        
        font_size = self.style.font_size or max(14, self.screen.height // 44)
        font = pg.font.SysFont(self.style.font_family, font_size)
        text_surface = font.render(display_text, True, text_color.to_tuple())
        text_rect = text_surface.get_rect(center=self.rect.center)
        self.screen.win.blit(text_surface, text_rect)
    
    def record_play(self) -> None:
        """Record that audio was played."""
        self.play_count += 1
    
    def reset_plays(self) -> None:
        """Reset play counter."""
        self.play_count = 0


class ToggleButton(Button):
    """
    A button that toggles between two states (e.g., Start/Stop).
    
    Usage:
        toggle = ToggleButton(
            screen, 
            text_off="Start Background",
            text_on="Stop Background",
            rel_x=0.5, rel_y=0.5
        )
        
        toggle.draw()
        if toggle.is_clicked(mouse_pos, clicked):
            toggle.toggle()
            if toggle.is_on:
                audio_engine.start_loop('background', pcm)
            else:
                audio_engine.stop_loop('background')
    """
    
    def __init__(
        self,
        screen: Screen,
        text_off: str,
        text_on: str,
        x: int | None = None,
        y: int | None = None,
        rel_x: float | None = None,
        rel_y: float | None = None,
        rel_width: float = 0.2,
        rel_height: float = 0.08,
        style_off: ButtonStyle | None = None,
        style_on: ButtonStyle | None = None,
        initially_on: bool = False
    ):
        # Default styles
        if style_off is None:
            style_off = ButtonStyle(bg_color=Colors.GREEN, text_color=Colors.BLACK)
        if style_on is None:
            style_on = ButtonStyle(bg_color=Colors.RED, text_color=Colors.WHITE)
        
        super().__init__(
            screen=screen,
            text=text_off,
            x=x, y=y,
            rel_x=rel_x, rel_y=rel_y,
            rel_width=rel_width, rel_height=rel_height,
            style=style_off
        )
        
        self.text_off = text_off
        self.text_on = text_on
        self.style_off = style_off
        self.style_on = style_on
        self.is_on = initially_on
    
    def toggle(self) -> bool:
        """Toggle state and return new state."""
        self.is_on = not self.is_on
        return self.is_on
    
    def set_on(self) -> None:
        """Set to ON state."""
        self.is_on = True
    
    def set_off(self) -> None:
        """Set to OFF state."""
        self.is_on = False
    
    def draw(self) -> None:
        """Draw toggle button in current state."""
        style = self.style_on if self.is_on else self.style_off
        text = self.text_on if self.is_on else self.text_off
        
        pg.draw.rect(self.screen.win, style.bg_color.to_tuple(), self.rect)
        pg.draw.rect(self.screen.win, style.border_color.to_tuple(), self.rect, style.border_width)
        
        font_size = style.font_size or max(14, self.screen.height // 45)
        font = pg.font.SysFont(style.font_family, font_size)
        text_surface = font.render(text, True, style.text_color.to_tuple())
        text_rect = text_surface.get_rect(center=self.rect.center)
        self.screen.win.blit(text_surface, text_rect)


class QuestionnaireScreen:
    """
    Complete questionnaire screen with question, options, and submit button.
    
    Handles single-select radio buttons with submit confirmation.
    
    Usage:
        q_screen = QuestionnaireScreen(
            screen=screen,
            question="How often do you experience this?",
            options=["Never", "Sometimes", "Often", "Always"]
        )
        
        response = q_screen.run()  # Returns selected option text
    """
    
    def __init__(
        self,
        screen: Screen,
        question: str,
        options: list[str],
        values: list[Any] | None = None,
        allow_back: bool = False,
        checkbox_style: CheckboxStyle | None = None,
        spacing_scalar: float = 1.5,
        max_question_y: float = 0.60
    ):
        self.screen = screen
        self.question = question
        self.options = options
        self.values = values
        self.allow_back = allow_back
        self.checkbox_style = checkbox_style
        self.spacing_scalar = spacing_scalar
        self.max_question_y = max_question_y
        self.text_renderer = TextRenderer(screen)
    
    def run(self) -> Any | None:
        """
        Run the questionnaire screen.
        
        Returns:
            Selected value, or None if user went back
        """
        pg.mouse.set_visible(True)
        
        # Calculate question position
        self.screen.fill()
        font_size = self.screen.scaled_font_size(20)
        style = TextStyle(font_size=font_size, align=TextAlign.LEFT)
        
        question_bottom = self.text_renderer.draw_paragraph(
            self.question,
            rel_x=0.05,
            rel_y=0.05,
            style=style,
            max_width=self.screen.abs_x(0.9),
            max_y=self.screen.abs_y(self.max_question_y)
        )
        
        # Create radio group
        group = RadioButtonGroup(
            screen=self.screen,
            options=self.options,
            question_y=question_bottom,
            style=self.checkbox_style,
            spacing_scalar=self.spacing_scalar,
            values=self.values
        )
        
        # Create submit button
        submit = SubmitButton(self.screen, "Submit")
        
        while True:
            self.screen.fill()
            
            # Redraw question
            self.text_renderer.draw_paragraph(
                self.question,
                rel_x=0.05,
                rel_y=0.05,
                style=style,
                max_width=self.screen.abs_x(0.9),
                max_y=self.screen.abs_y(self.max_question_y)
            )
            
            # Draw options and submit
            group.draw()
            submit.draw(enabled=group.has_selection())
            
            self.screen.update()
            
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        self.screen.handle_escape()
                    if event.key == pg.K_LEFT and self.allow_back:
                        return None
                
                elif event.type == pg.MOUSEBUTTONUP:
                    mouse_pos = pg.mouse.get_pos()
                    
                    # Handle option clicks
                    group.handle_click(mouse_pos, True)
                    
                    # Handle submit click
                    if submit.is_clicked(mouse_pos, True) and group.has_selection():
                        return group.get_selected()


class Questionnaire:
    """
    Multi-question questionnaire with navigation.
    
    Supports multiple questions with the same or different option sets.
    
    Usage:
        q = Questionnaire(
            screen=screen,
            questions=[
                ("Question 1?", ["Yes", "No"]),
                ("Question 2?", ["Never", "Sometimes", "Always"]),
            ]
        )
        
        responses = q.run()  # Returns list of responses
    """
    
    def __init__(
        self,
        screen: Screen,
        questions: list[tuple[str, list[str]]],
        values: list[list[Any]] | None = None,
        intro_text: str | None = None,
        checkbox_style: CheckboxStyle | None = None
    ):
        self.screen = screen
        self.questions = questions
        self.values = values
        self.intro_text = intro_text
        self.checkbox_style = checkbox_style
        self.text_renderer = TextRenderer(screen)
    
    def run(self) -> list[Any]:
        """
        Run the full questionnaire.
        
        Returns:
            List of responses (one per question)
        """
        responses: list[Any] = []
        
        # Show intro if provided
        if self.intro_text:
            self.screen.fill()
            pg.mouse.set_visible(False)
            style = TextStyle(font_size=self.screen.scaled_font_size(20))
            self.text_renderer.draw_paragraph(
                self.intro_text,
                rel_x=0.05, rel_y=0.05,
                style=style,
                max_width=self.screen.abs_x(0.9)
            )
            self.screen.update()
            wait_for_key(pg.K_SPACE)
        
        # Process each question
        question_idx = 0
        while question_idx < len(self.questions):
            q_text, q_opts = self.questions[question_idx]
            q_vals = self.values[question_idx] if self.values and question_idx < len(self.values) else None
            
            q_screen = QuestionnaireScreen(
                screen=self.screen,
                question=q_text,
                options=q_opts,
                values=q_vals,
                allow_back=(question_idx > 0),
                checkbox_style=self.checkbox_style
            )
            
            result = q_screen.run()
            
            if result is None and question_idx > 0:
                # User went back
                question_idx -= 1
                responses.pop()
            elif result is not None:
                responses.append(result)
                question_idx += 1
        
        return responses


# =============================================================================
# EXTENDED SCREEN BUILDER METHODS
# =============================================================================

def questionnaire_screen(
    win: pg.Surface,
    question: str,
    options: list[str],
    values: list[Any] | None = None
) -> Any | None:
    """Quick utility to show a single questionnaire question."""
    screen = Screen(win)
    q = QuestionnaireScreen(screen, question, options, values)
    return q.run()


def paged_screen(
    win: pg.Surface,
    pages: list[str],
    allow_back: bool = True
) -> int:
    """Quick utility to show paged content with arrow navigation."""
    screen = Screen(win)
    paged = PagedScreen(screen, pages, allow_back)
    return paged.run()
