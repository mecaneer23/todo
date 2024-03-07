# pylint: disable=missing-docstring

from enum import Enum
from typing import Iterable, NamedTuple

from src.get_args import CHECKBOX, INDENT
from src.utils import Chunk, Color


class BoxChar(Enum):
    MINUS = 0
    PLUS = 1
    NONE = 2

    @staticmethod
    def from_str(string: str) -> "BoxChar":
        return {
            "-": BoxChar.MINUS,
            "+": BoxChar.PLUS,
        }[string]

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return {
            BoxChar.PLUS: "+",
            BoxChar.MINUS: "-",
            BoxChar.NONE: "",
        }[self]


class Todo:
    def __init__(self, text: str = "") -> None:
        self.box_char: BoxChar = BoxChar.NONE
        self.color: Color = Color.WHITE
        self.display_text: str = ""
        self.text: str = ""
        self.indent_level: int = 0
        self.call_init(text)

    def _init_box_char(self, pointer: int) -> tuple[BoxChar, int]:
        if len(self.text) > pointer and self.text[pointer] in "-+":
            return BoxChar.from_str(self.text[pointer]), pointer + 1
        return BoxChar.NONE, pointer

    def _init_color(self, pointer: int) -> tuple[Color, int]:
        if (
            len(self.text) > pointer + 1
            and self.text[pointer].isdigit()
            and self.text[pointer + 1] == " "
        ):
            return Color(int(self.text[pointer])), pointer + 2
        return Color.WHITE, pointer

    def _init_attrs(self) -> tuple[BoxChar, Color, str]:
        pointer = self.indent_level
        box_char, pointer = self._init_box_char(pointer)
        color, pointer = self._init_color(pointer)
        if len(self.text) > pointer and self.text[pointer] == " ":
            pointer += 1
        display_text = self.text[pointer:]

        return box_char, color, display_text

    def call_init(self, text: str) -> None:
        self.text = text
        self.indent_level = len(text) - len(text.lstrip())
        if not self.text:
            self.box_char = BoxChar.MINUS
            self.color = Color.WHITE
            self.display_text = ""
            return
        self.box_char, self.color, self.display_text = self._init_attrs()

    def __getitem__(self, key: int) -> str:
        return self.text[key]

    def __len__(self) -> int:
        return len(self.display_text)

    def set_display_text(self, display_text: str) -> "Todo":
        self.display_text = display_text
        self.text = repr(self)
        return self

    def is_toggled(self) -> bool:
        if self.box_char == BoxChar.NONE:
            return False
        return self.box_char == BoxChar.PLUS

    def set_indent_level(self, indent_level: int) -> None:
        self.indent_level = indent_level

    def set_color(self, color: Color) -> None:
        self.color = color

    def get_box(self) -> str:
        return {
            BoxChar.PLUS: f"{CHECKBOX}  ",
            BoxChar.MINUS: "☐  ",
            BoxChar.NONE: "",
        }[self.box_char]

    def get_simple_box(self) -> str:
        return {
            BoxChar.PLUS: "[x] ",
            BoxChar.MINUS: "[ ] ",
            BoxChar.NONE: "",
        }[self.box_char]

    def has_box(self) -> bool:
        return self.box_char != BoxChar.NONE

    def is_empty(self) -> bool:
        return self.display_text == ""

    def toggle(self) -> None:
        self.box_char = {
            BoxChar.PLUS: BoxChar.MINUS,
            BoxChar.MINUS: BoxChar.PLUS,
            BoxChar.NONE: BoxChar.NONE,
        }[self.box_char]
        self.text = repr(self)

    def indent(self) -> None:
        self.indent_level += INDENT
        self.text = repr(self)

    def dedent(self) -> None:
        if self.indent_level >= INDENT:
            self.indent_level -= INDENT
            self.text = repr(self)

    def copy(self) -> "Todo":
        return Todo(repr(self))

    def __repr__(self) -> str:
        chunks: tuple[Chunk, ...] = (
            Chunk(True, self.indent_level * " "),
            Chunk(
                self.box_char != BoxChar.NONE and not self.is_empty(),
                str(self.box_char),
            ),
            Chunk(self.color != Color.WHITE, str(self.color.as_int())),
            Chunk(
                (self.box_char != BoxChar.NONE and not self.is_empty())
                or self.color != Color.WHITE,
                " ",
            ),
            Chunk(True, self.display_text),
        )
        return "".join([item for condition, item in chunks if condition])


class Todos(list[Todo]):
    """Wrapper around list of Todo objects"""
    def __init__(self, iterable: Iterable[Todo]) -> None:
        super().__init__(iterable)


class TodoList(NamedTuple):
    """
    An object representing the todos
    and a cursor within the list
    """

    todos: Todos
    cursor: int
