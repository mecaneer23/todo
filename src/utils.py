"""
General utilities, useful across multiple other files
"""

from enum import Enum
from typing import Any, NamedTuple

from src.get_args import TKINTER_GUI

if TKINTER_GUI:
    from src.tcurses import curses
else:
    import curses


class Chunk(NamedTuple):
    """
    A chunk of text that can be toggled on or off based on a condition
    """

    condition: bool
    text: str


class Color(Enum):
    """
    Standardized colors for Ndo
    """

    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7

    def as_int(self) -> int:
        """
        Main getter for Ndo colors
        """
        return self.value

    def as_char(self) -> str:
        """Get lowercase first letter of color"""
        return self.name[0].lower()

    @staticmethod
    def from_first_char(char: str) -> "Color":
        """Return the color corresponding to its first character"""
        return {
            "r": Color.RED,
            "g": Color.GREEN,
            "y": Color.YELLOW,
            "b": Color.BLUE,
            "m": Color.MAGENTA,
            "c": Color.CYAN,
            "w": Color.WHITE,
        }[char]

    @staticmethod
    def as_dict() -> dict[str, int]:
        """
        Get all colors represented as a mapping of color name to corresponding int value
        """
        return dict((color.name.capitalize(), color.value) for color in Color)


def clamp(number: int, minimum: int, maximum: int) -> int:
    """
    Clamp a number in between a minimum and maximum.
    """
    return min(max(number, minimum), maximum - 1)


def set_header(stdscr: Any, message: str) -> None:
    """
    Set the header to a specific message.
    """
    stdscr.addstr(
        0, 0, message.ljust(stdscr.getmaxyx()[1]), curses.A_BOLD | curses.color_pair(2)
    )


def overflow(counter: int, minimum: int, maximum: int) -> int:
    """
    Similar to clamp(), but instead of keeping a counter between
    two values, by leaving it at the min or max end, it wraps over
    the top or bottom.
    """
    if counter >= maximum:
        return minimum + (counter - maximum)
    if counter < minimum:
        return maximum - (minimum - counter)
    return counter
