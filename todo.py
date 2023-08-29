#!/usr/bin/env python3
# pyright: reportMissingModuleSource=false

import curses
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
from pathlib import Path
from re import match as re_match
from typing import Any, Callable, TypeVar

T = TypeVar("T")
AUTOSAVE = True
BULLETS = False
CONTROLS_BEGIN_INDEX = 47
CONTROLS_END_INDEX = 71
DEFAULT_TODO = "todo.txt"
ENUMERATE = False
FILENAME = Path(DEFAULT_TODO)
HEADER = ""
HELP_FILE = Path(__file__).parent.joinpath("README.md").absolute()
INDENT = 2
NO_GUI = False
RELATIVE_ENUMERATE = False
SIMPLE_BOXES = False
STRIKETHROUGH = False

COLORS = {
    "Red": 1,
    "Green": 2,
    "Yellow": 3,
    "Blue": 4,
    "Magenta": 5,
    "Cyan": 6,
    "White": 7,
}


class Todo:
    def __init__(self, text: str = "") -> None:
        self.box_char: str | None = None
        self.color: int = 7
        self.display_text: str = ""
        self.text: str = ""
        self.indent_level: int = 0
        self.call_init(text)

    def _init_box_char(self, pointer: int) -> tuple[str | None, int]:
        if self.text[pointer] in "-+":
            return self.text[pointer], pointer + 1
        return None, pointer

    def _init_color(self, pointer: int) -> tuple[int, int]:
        if self.text[pointer].isdigit():
            return int(self.text[pointer]), pointer + 2
        return 7, pointer

    def _init_attrs(self) -> tuple[str | None, int, str]:
        pointer = self.indent_level
        box_char, pointer = self._init_box_char(pointer)
        color, pointer = self._init_color(pointer)
        if self.text[pointer] == " ":
            pointer += 1
        display_text = self.text[pointer:]

        return box_char, color, display_text

    def call_init(self, text: str) -> None:
        self.text = text
        self.indent_level = len(text) - len(text.lstrip())
        if self.text == "":
            self.box_char = "-"
            self.color = 7
            self.display_text = ""
            return
        self.box_char, self.color, self.display_text = self._init_attrs()

    def __getitem__(self, key: int) -> str:
        return self.text[key]

    def set_display_text(self, display_text: str) -> None:
        self.display_text = display_text
        self.text = repr(self)

    def is_toggled(self) -> bool:
        if self.box_char is None:
            return False
        return self.box_char == "+"

    def set_indent_level(self, indent_level: int) -> None:
        self.indent_level = indent_level

    def set_color(self, color: int) -> None:
        self.color = color

    def get_box(self) -> str:
        table = (
            {
                "+": "☑  ",
                "-": "☐  ",
                None: "",
            }
            if not SIMPLE_BOXES
            else {
                "+": "[x] ",
                "-": "[ ] ",
                None: "",
            }
        )

        if self.box_char in table:
            return table[self.box_char]
        raise KeyError(
            f"The completion indicator of `{self.text}` is not one of (+, -)"
        )

    def has_box(self) -> bool:
        return self.box_char is not None

    def is_empty(self) -> bool:
        return self.display_text == ""

    def toggle(self) -> None:
        self.box_char = {"+": "-", "-": "+", None: ""}[self.box_char]
        self.text = repr(self)

    def indent(self) -> None:
        self.indent_level += INDENT
        self.text = repr(self)

    def dedent(self) -> None:
        if self.indent_level >= INDENT:
            self.indent_level -= INDENT
            self.text = repr(self)

    def __repr__(self) -> str:
        return "".join(
            [
                self.indent_level * " ",
                self.box_char if self.box_char is not None else "",
                str(self.color) if self.color != 7 else "",
                " " if self.box_char is not None or self.color != 7 else "",
                self.display_text,
            ]
        )


class UndoRedo:
    def __init__(self) -> None:
        self.history: list[
            tuple[Callable[..., tuple[list[Todo], int] | list[Todo] | int], Any]
        ] = []
        self.redos: list[
            tuple[Callable[..., tuple[list[Todo], int] | list[Todo] | int], Any]
        ] = []
        self.index = -1

    def handle_return(
        self,
        undo_or_redo: Callable[..., tuple[list[Todo], int] | list[Todo] | int],
        todos: list[Todo],
        selected: int,
    ) -> tuple[list[Todo], int]:
        """
        this is the only non-reusable function from this class
        This function takes in a list of current values and
        returns a list with the values after being undone
        """
        returns = undo_or_redo(todos, selected)
        if isinstance(returns, tuple):
            return returns
        elif isinstance(returns, list):
            return returns, selected
        elif isinstance(returns, int):
            return todos, returns
        else:
            return todos, selected

    def undo(
        self, todos: list[Todo], selected: int
    ) -> tuple[list[Todo], int] | list[Todo] | int:
        if self.index < 0:
            return todos, selected
        func, args = self.history[self.index]
        self.index -= 1
        return func(*args)

    def redo(
        self, todos: list[Todo], selected: int
    ) -> tuple[list[Todo], int] | list[Todo] | int:
        if self.index >= len(self.history) - 1:
            return todos, selected
        self.index += 1
        func, args = self.redos[self.index]
        return func(*args)

    def add_undo(self, revert_with: Callable[..., Any], *args: Any) -> None:
        self.history.append((revert_with, deepcopy_ignore([*args])))
        self.index = len(self.history) - 1

    def do(self, func: Callable[..., T], *args: Any) -> T:
        # TODO: implement redo
        # I have the redo function and the
        # args it needs... how should I store it?
        # self.redos.append((func, deepcopy_ignore(args).append(args[1][args[2]])
        # if func.__name__ == "new_todo_next" else deepcopy_ignore(args)))
        return func(*args)

    def __repr__(self) -> str:
        return "\n".join(f"{i[0].__name__}: {i[1]}" for i in self.history)


class Cursor:
    def __init__(self, position: int, *positions: int) -> None:
        self.positions: list[int] = [position, *positions]
        self.direction: str | None = None

    def __len__(self) -> int:
        return len(self.positions)

    def __str__(self) -> str:
        return str(self.positions[0])

    def __int__(self) -> int:
        return self.positions[0]

    def __contains__(self, child: int) -> bool:
        return child in self.positions

    def set_to(self, position: int) -> None:
        self.positions = [position]

    def todo_set_to(self, todo_position: tuple[list[Todo], int]) -> list[Todo]:
        self.positions[0] = todo_position[1]
        return todo_position[0]

    def set_multiple(self, positions: list[int]) -> None:
        self.positions = positions

    def select_next(self) -> None:
        self.positions.append(max(self.positions) + 1)
        self.positions.sort()

    def deselect_next(self) -> None:
        if len(self.positions) > 1:
            self.positions.remove(max(self.positions))

    def deselect_prev(self) -> None:
        if len(self.positions) > 1:
            self.positions.remove(min(self.positions))

    def select_prev(self) -> None:
        self.positions.append(min(self.positions) - 1)
        self.positions.sort()

    def get_deletable(self) -> list[int]:
        return [min(self.positions) for _ in self.positions]

    def multiselect_down(self, max_len: int) -> None:
        if max(self.positions) >= max_len - 1:
            return
        if len(self.positions) == 1 or self.direction == "down":
            self.select_next()
            self.direction = "down"
            return
        self.deselect_prev()

    def multiselect_up(self) -> None:
        if min(self.positions) == 0 and self.direction == "up":
            return
        if len(self.positions) == 1 or self.direction == "up":
            self.select_prev()
            self.direction = "up"
            return
        self.deselect_next()

    def multiselect_top(self) -> None:
        for _ in range(self.positions[0], 0, -1):
            self.multiselect_up()

    def multiselect_bottom(self, max_len: int) -> None:
        for _ in range(self.positions[0], max_len):
            self.multiselect_down(max_len)

    def multiselect_to(self, position: int, max_len: int) -> None:
        direction = -1 if position < self.positions[0] else 1
        for _ in range(self.positions[0], position, direction):
            if direction == 1:
                self.multiselect_down(max_len)
                continue
            self.multiselect_up()

    def multiselect_from(self, stdscr: Any, first_digit: int, max_len: int) -> None:
        total = str(first_digit)
        while True:
            try:
                key = stdscr.getch()
            except KeyboardInterrupt:  # exit on ^C
                return
            if key != 27:  # not an escape sequence
                return
            stdscr.nodelay(True)
            subch = stdscr.getch()  # alt + ...
            stdscr.nodelay(False)
            if subch == 107:  # k
                self.multiselect_to(self.positions[0] - int(total), max_len)
            elif subch == 106:  # j
                self.multiselect_to(self.positions[0] + int(total), max_len)
            elif subch in range(48, 58):  # digits
                total += str(subch - 48)
                continue
            return


class Mode:
    def __init__(self, toggle_mode: bool) -> None:
        self.toggle_mode = toggle_mode

    def toggle(self) -> None:
        self.toggle_mode = not self.toggle_mode


class ExternalModuleNotFoundError(Exception):
    def __init__(self, module: str, todos: list[Todo], operation: str):
        update_file(FILENAME, todos, True)
        exit(
            f"`{module}` module required for {operation} operation. "
            f"Try `pip install {module}`"
        )


def read_file(filename: Path) -> str:
    if not filename.exists():
        with filename.open("w"):
            return ""
    with filename.open() as f:
        return f.read()


def validate_file(raw_data: str) -> list[Todo]:
    if len(raw_data) == 0:
        return []
    usable_data: list[Todo] = []
    for line in raw_data.split("\n"):
        if len(line) == 0:
            usable_data.append(Todo())  # empty todo
        elif re_match(r"^( *)?([+-])\d? .*$", line):
            usable_data.append(Todo(line))
        elif re_match(r"^( *\d )?.*$", line):
            usable_data.append(Todo(line))  # note
        else:
            raise ValueError(f"Invalid todo: {line}")
    return usable_data


def is_file_externally_updated(filename: Path, todos: list[Todo]) -> bool:
    with filename.open() as f:
        return not validate_file(f.read()) == todos


def get_args() -> Namespace:
    parser = ArgumentParser(
        description="Ndo is a todo list program to help you manage your todo lists",
        add_help=False,
        formatter_class=RawDescriptionHelpFormatter,
        epilog="Controls:\n  "
        + "\n  ".join(
            md_table_to_lines(
                CONTROLS_BEGIN_INDEX,
                CONTROLS_END_INDEX,
                str(HELP_FILE),
                ("<kbd>", "</kbd>"),
            )
        ),
    )
    parser.add_argument(
        "filename",
        type=str,
        nargs="?",
        default=FILENAME,
        help=f"Provide a filename to store the todo list in.\
            Default is `{FILENAME}`.",
    )
    parser.add_argument(
        "--autosave",
        "-a",
        action="store_true",
        default=AUTOSAVE,
        help=f"Boolean: determines if file is saved on every\
            action or only once at the program termination.\
            Default is `{AUTOSAVE}`.",
    )
    parser.add_argument(
        "--bullet-display",
        "-b",
        action="store_true",
        default=BULLETS,
        help=f"Boolean: determine if Notes are displayed with\
            a bullet point in front or not. Default is `{BULLETS}`.",
    )
    parser.add_argument(
        "--enumerate",
        "-e",
        action="store_true",
        default=ENUMERATE,
        help=f"Boolean: determines if todos are numbered when\
            printed or not. Default is `{ENUMERATE}`.",
    )
    parser.add_argument(
        "--help",
        "-h",
        action="help",
        help="Show this help message and exit.",
    )
    parser.add_argument(
        "--help-file",
        type=str,
        default=HELP_FILE,
        help=f"Allows passing alternate file to\
        specify help menu. Default is `{HELP_FILE}`.",
    )
    parser.add_argument(
        "--indentation-level",
        "-i",
        type=int,
        default=INDENT,
        help=f"Allows specification of indentation level. \
            Default is `{INDENT}`.",
    )
    parser.add_argument(
        "--no-gui",
        "-n",
        action="store_true",
        default=NO_GUI,
        help=f"Boolean: If true, do not start a curses gui,\
            rather, just print out the todo list. Default is\
            `{NO_GUI}`.",
    )
    parser.add_argument(
        "--relative-enumeration",
        "-r",
        action="store_true",
        default=RELATIVE_ENUMERATE,
        help=f"Boolean: determines if todos are numbered\
            when printed. Numbers relatively rather than\
            absolutely. Default is `{RELATIVE_ENUMERATE}`.",
    )
    parser.add_argument(
        "--simple-boxes",
        "-x",
        action="store_true",
        default=SIMPLE_BOXES,
        help=f"Boolean: allow rendering simpler checkboxes if\
            terminal doesn't support default ascii checkboxes.\
            Default is `{SIMPLE_BOXES}`.",
    )
    parser.add_argument(
        "--strikethrough",
        "-s",
        action="store_true",
        default=STRIKETHROUGH,
        help=f"Boolean: strikethrough completed todos\
            - option to disable because some terminals\
            don't support strikethroughs. Default is\
            `{STRIKETHROUGH}`.",
    )
    parser.add_argument(
        "--title",
        "-t",
        type=str,
        nargs="+",
        default=HEADER,
        help="Allows passing alternate header.\
            Default is filename.",
    )
    return parser.parse_args()


def handle_args(args: Namespace) -> None:
    global AUTOSAVE
    global BULLETS
    global ENUMERATE
    global FILENAME
    global HEADER
    global HELP_FILE
    global INDENT
    global NO_GUI
    global RELATIVE_ENUMERATE
    global SIMPLE_BOXES
    global STRIKETHROUGH
    AUTOSAVE = args.autosave
    BULLETS = args.bullet_display
    ENUMERATE = args.enumerate
    FILENAME = (
        Path(args.filename, DEFAULT_TODO)
        if Path(args.filename).is_dir()
        else Path(args.filename)
    )
    HEADER = FILENAME.as_posix() if args.title == HEADER else " ".join(args.title)
    HELP_FILE = Path(args.help_file)
    INDENT = args.indentation_level
    NO_GUI = args.no_gui
    RELATIVE_ENUMERATE = args.relative_enumeration
    SIMPLE_BOXES = args.simple_boxes
    STRIKETHROUGH = args.strikethrough


def deepcopy_ignore(lst: list[Any]) -> list[Any]:
    from copy import deepcopy

    from _curses import window as curses_window

    return [i if isinstance(i, curses_window) else deepcopy(i) for i in lst]


def clamp(counter: int, minimum: int, maximum: int) -> int:
    return min(max(counter, minimum), maximum - 1)


def update_file(filename: Path, lst: list[Todo], save: bool = AUTOSAVE) -> int:
    if not save:
        return 0
    with filename.open("w", newline="\n") as f:
        return f.write("\n".join(map(repr, lst)))


def _print(message: str, end: str = "\n") -> None:
    with open("debugging/log.txt", "a") as f:
        f.write(f"{message}{end}")


def wgetnstr_success(todo: Todo, chars: list[str]) -> Todo:
    todo.set_display_text("".join(chars))
    return todo


def wgetnstr(
    stdscr: Any,
    win: Any,
    todo: Todo,
    prev_todo: Todo,
    mode: Mode | None = None,
    n: int = 1024,
) -> Todo:
    """
    Reads a string from the given window. Returns a todo from the user
    Functions like a JavaScript alert box for user input.

    Args:
        stdscr (Window object):
            Main window of the entire program. Only used in
            calls to set_header().
        win (Window object):
            The window to read from. The entire window
            will be used, so a curses.newwin() should be
            generated specifically for use with this
            function. As a box will be created around the
            window's border, the window must have a minimum
            height of 3 characters. The width will determine
            a maximum value of n.
        todo (Todo):
            Pass a Todo object to initially occupy the window.
        prev_todo (Todo):
            Pass a Todo object to copy the color, indentation
            level, box character, etc from. This is only used
            if `todo` is empty.
        mode (Mode, optional):
            If adding todos in entry mode (used for rapid
            repetition), allow toggling of that mode by
            passing a Mode object.
        n (int, optional):
            Max number of characters in the read string.
            It might error if this number is greater than
            the area of the window. Defaults to 1024.

    Raises:
        ValueError:
            If the window is too short to display the minimum
            1 line of text.
        NotImplementedError:
            If the window is too long to display the maximum
            n characters.

    Returns:
        Todo: Similar to the built in input() function,
        returns a Todo object containing the user's entry.
    """
    if win.getmaxyx()[0] < 3:
        raise ValueError(
            "Window is too short, it won't be able to\
            display the minimum 1 line of text."
        )
    elif win.getmaxyx()[0] > 3:
        raise NotImplementedError("Multiline text editing is not supported")
    if todo.is_empty():
        todo.set_indent_level(prev_todo.indent_level)
        todo.set_color(prev_todo.color)
        if not prev_todo.has_box():
            todo.box_char = None
    original = todo
    chars = list(todo.display_text)
    position = len(chars)
    win.box()
    win.nodelay(False)
    while True:
        if position == len(chars):
            if len(chars) + 1 >= win.getmaxyx()[1] - 1:
                return wgetnstr_success(todo, chars)
            win.addstr(1, len(chars) + 1, "█")
        for i, v in enumerate("".join(chars).ljust(win.getmaxyx()[1] - 2)):
            win.addstr(1, i + 1, v, curses.A_REVERSE if i == position else 0)
        win.refresh()
        try:
            ch = win.getch()
        except KeyboardInterrupt:  # ctrl+c
            if mode is not None:
                mode.toggle()
            return original
        if ch in (10, 13):  # enter
            break
        elif ch in (8, 127, 263):  # backspace
            if position > 0:
                position -= 1
                chars.pop(position)
        elif ch in (24, 11):  # ctrl + x/k
            if mode is not None:
                mode.toggle()
                return wgetnstr_success(todo, chars)
        elif ch == 23:  # ctrl + backspace
            while True:
                if position <= 0:
                    break
                position -= 1
                if chars[position] == " ":
                    chars.pop(position)
                    break
                chars.pop(position)
        elif ch == 9:  # tab
            todo.indent()
            set_header(stdscr, f"Tab level: {todo.indent_level // INDENT} tabs")
            stdscr.refresh()
        elif ch == 27:  # any escape sequence `^[`
            win.nodelay(True)
            escape = win.getch()  # skip `[`
            if escape == -1:  # escape
                if mode is not None:
                    mode.toggle()
                return original
            elif escape == 100:  # ctrl + delete
                if position < len(chars) - 1:
                    chars.pop(position)
                    position -= 1
                while True:
                    if position >= len(chars) - 1:
                        break
                    position += 1
                    if chars[position] == " ":
                        break
                    chars.pop(position)
                    position -= 1
                continue
            win.nodelay(False)
            try:
                subch = win.getch()
            except KeyboardInterrupt:
                return original
            if subch == 68:  # left arrow
                if position > 0:
                    position -= 1
            elif subch == 67:  # right arrow
                if position < len(chars):
                    position += 1
            elif subch == 51:  # delete
                win.getch()  # skip the `~`
                if position < len(chars):
                    chars.pop(position)
            elif subch == 49:  # ctrl + arrow
                for _ in range(2):  # skip the `;5`
                    win.getch()
                direction = win.getch()
                if direction == 67:  # right arrow
                    while True:
                        if position >= len(chars) - 1:
                            break
                        position += 1
                        if chars[position] == " ":
                            break
                elif direction == 68:  # left arrow
                    while True:
                        if position <= 0:
                            break
                        position -= 1
                        if chars[position] == " ":
                            break
            elif subch == 72:  # home
                position = 0
            elif subch == 70:  # end
                position = len(chars)
            elif subch == 90:  # shift + tab
                todo.dedent()
                set_header(stdscr, f"Tab level: {todo.indent_level // INDENT} tabs")
                stdscr.refresh()
            else:
                raise ValueError(repr(subch))
        else:  # typable characters (basically alphanum)
            if len(chars) >= n:
                curses.beep()
                continue
            if ch == -1:
                continue
            chars.insert(position, chr(ch))
            if position < len(chars):
                position += 1

    return wgetnstr_success(todo, chars)


def hline(win: Any, y: int, x: int, ch: str | int, n: int) -> None:
    win.addch(y, x, curses.ACS_LTEE)
    win.hline(y, x + 1, ch, n - 2)
    win.addch(y, x + n - 1, curses.ACS_RTEE)


def insert_todo(
    stdscr: Any, todos: list[Todo], index: int, mode: Mode | None = None
) -> list[Todo]:
    y, x = stdscr.getmaxyx()
    todo = wgetnstr(
        stdscr,
        curses.newwin(3, x * 3 // 4, y // 2 - 3, x // 8),
        todo=Todo(),
        prev_todo=todos[index - 1],
        mode=mode,
    )
    if todo.is_empty():
        return todos
    todos.insert(index, todo)
    return todos


def insert_empty_todo(todos: list[Todo], index: int) -> list[Todo]:
    todos.insert(index, Todo())
    return todos


def search(stdscr: Any, todos: list[Todo], selected: Cursor) -> None:
    set_header(stdscr, "Searching...")
    stdscr.refresh()
    y, x = stdscr.getmaxyx()
    sequence = wgetnstr(
        stdscr, curses.newwin(3, x * 3 // 4, y // 2 - 3, x // 8), Todo(), Todo()
    ).display_text
    stdscr.clear()
    for i, todo in enumerate(todos[int(selected) :], start=int(selected)):
        if sequence in todo.display_text:
            break
    else:
        selected.set_to(0)
        return
    selected.set_to(i)


def set_header(stdscr: Any, message: str) -> None:
    stdscr.addstr(0, 0, message.ljust(stdscr.getmaxyx()[1]), curses.A_BOLD)


def remove_todo(todos: list[Todo], index: int) -> list[Todo]:
    if len(todos) < 1:
        return todos
    todos.pop(index)
    return todos


def strikethrough(text: str) -> str:
    return "\u0336".join(text) if STRIKETHROUGH else text


def swap_todos(todos: list[Todo], idx1: int, idx2: int) -> list[Todo]:
    if min(idx1, idx2) >= 0 and max(idx1, idx2) < len(todos):
        todos[idx1], todos[idx2] = todos[idx2], todos[idx1]
    return todos


def md_table_to_lines(
    first_line_idx: int,
    last_line_idx: int,
    filename: str = "README.md",
    remove: tuple[str, ...] = (),
) -> list[str]:
    """
    Converts a Markdown table to a list of formatted strings.

    Args:
        first_line_idx (int): The index of the first line of the Markdown
        table to be converted.
        last_line_idx (int): The index of the last line of the Markdown
        table to be converted.
        filename (str, optional): The name of the markdown file containing the
        table. Default is "README.md".
        remove (list[str], optional): The list of strings to be removed from each line.
        This is in the case of formatting that should exist in markdown but not
        python. Default is an empty list.

    Returns:
        list[str]: A list of formatted strings representing the converted
        Markdown table.

    Raises:
        ValueError: If the last line index is less than or equal to the
        first line index.
        FileNotFoundError: If the specified markdown file cannot be found.
    """

    # Check for valid line indices
    if last_line_idx <= first_line_idx:
        raise ValueError("Last line index must be greater than first line index.")

    # Get raw lines from the markdown file
    try:
        with open(filename) as f:
            lines = f.readlines()[first_line_idx - 1 : last_line_idx - 1]
    except FileNotFoundError:
        raise FileNotFoundError("Markdown file not found.")

    # Remove unwanted characters and split each line into a list of values
    split_lines: list[list[str]] = [[]] * len(lines)
    for i, _ in enumerate(lines):
        for item in remove:
            lines[i] = lines[i].replace(item, "")
        split_lines[i] = lines[i].split("|")[1:-1]
    column_count = len(split_lines[0])
    split_lines[1] = ["-" for _ in range(column_count)]

    # Create lists of columns
    columns: list[list[Any]] = [[0, []] for _ in range(column_count)]
    for i in range(column_count):
        for line in split_lines:
            columns[i][1].append(line[i])

    # Find the maximum length of each column
    for i, (_, v) in enumerate(columns):
        columns[i][0] = len(max([w.strip() for w in v], key=len))
    split_lines[1] = ["-" * (length + 1) for length, _ in columns]

    # Join the lines together into a list of formatted strings
    joined_lines: list[str] = [""] * len(split_lines)
    for i, line in enumerate(split_lines):
        for j, v in enumerate(line):
            line[j] = v.strip().ljust(columns[j][0] + 2)
        joined_lines[i] = "".join(split_lines[i])
    joined_lines[1] = "-" * (
        sum(columns[i][0] for i, _ in enumerate(columns)) + 2 * (len(columns) - 1)
    )
    return joined_lines


def help_menu(parent_win: Any) -> None:
    parent_win.clear()
    set_header(parent_win, "Help (k/j to scroll):")
    lines = []
    for line in md_table_to_lines(
        CONTROLS_BEGIN_INDEX,
        CONTROLS_END_INDEX,
        str(HELP_FILE),
        ("<kbd>", "</kbd>", "(arranged alphabetically)"),
    ):
        lines.append(line[:-2])
    win = curses.newwin(
        min(parent_win.getmaxyx()[0] - 1, len(lines) + 2),
        len(lines[0]) + 2,
        1,
        (parent_win.getmaxyx()[1] - (len(lines[0]) + 1)) // 2,
    )
    win.box()
    parent_win.refresh()
    cursor = 0
    win.addstr(1, 1, lines[0])
    hline(win, 2, 0, curses.ACS_HLINE, win.getmaxyx()[1])
    while True:
        new_lines, _ = make_printable_sublist(
            win.getmaxyx()[0] - 4, lines[2:], cursor, 0
        )
        for i, v in enumerate(new_lines):
            win.addstr(i + 3, 1, v)
        win.refresh()
        try:
            key = win.getch()
        except KeyboardInterrupt:  # exit on ^C
            break
        if key in (259, 107):  # up | k
            cursor = clamp(cursor - 1, 0, len(lines) - 2)
        elif key in (258, 106, 10):  # down | j | enter
            cursor = clamp(cursor + 1, 0, len(lines) - len(new_lines) - 1)
        else:
            break
    parent_win.clear()


def magnify(stdscr: Any, todos: list[Todo], selected: Cursor) -> None:
    try:
        from pyfiglet import figlet_format as big
    except ModuleNotFoundError:
        raise ExternalModuleNotFoundError("pyfiglet", todos, "magnify")

    stdscr.clear()
    set_header(stdscr, "Magnifying...")
    big_text = big(todos[int(selected)].display_text, width=stdscr.getmaxyx()[1]).split(
        "\n"
    )
    first_column = max((stdscr.getmaxyx()[1] - len(max(big_text, key=len))) // 2, 0)
    first_row = max((stdscr.getmaxyx()[0] - len(big_text)) // 2 + 1, 1)
    for i, line in enumerate(big_text):
        for count, char in enumerate(line):
            if (
                first_row + i >= stdscr.getmaxyx()[0] - 1
                or first_column + count >= stdscr.getmaxyx()[1] - 1
            ):
                continue
            stdscr.addch(first_row + i, first_column + count, char)
    stdscr.refresh()
    stdscr.getch()
    stdscr.clear()


def get_color(color: str) -> int:
    return COLORS[color]


def color_menu(parent_win: Any, original: int) -> int:
    parent_win.clear()
    set_header(parent_win, "Colors:")
    lines = [i.ljust(len(max(COLORS.keys(), key=len))) for i in COLORS.keys()]
    win = curses.newwin(
        len(lines) + 2,
        len(lines[0]) + 2,
        1,
        (parent_win.getmaxyx()[1] - (len(lines[0]) + 1)) // 2,
    )
    win.box()
    selected = original - 1
    while True:
        parent_win.refresh()
        for i, v in enumerate(lines):
            win.addstr(
                i + 1,
                1,
                v,
                curses.color_pair(get_color(v.strip()))
                | (curses.A_REVERSE if i == selected else 0),
            )
        try:
            key = win.getch()
        except KeyboardInterrupt:
            return original
        if key == 107:  # k
            selected -= 1
        elif key == 106:  # j
            selected += 1
        elif key == 103:  # g
            selected = 0
        elif key == 71:  # G
            selected = len(lines)
        elif key in (113, 27):  # q | esc
            return original
        elif key == 10:  # enter
            return get_color(lines[selected].strip())
        elif key in range(49, 56):  # numbers
            selected = key - 49
        else:
            continue
        selected = clamp(selected, 0, len(lines))
        parent_win.refresh()
        win.refresh()


def get_indented_sections(todos: list[Todo]) -> list[list[Todo]]:
    indented_sections = []
    section = []
    for todo in todos:
        if todo.indent_level > 0:
            section.append(todo)
            continue
        if len(section) > 0:
            indented_sections.append(section)
        section = [todo]
    indented_sections.append(section)
    return indented_sections


def flatten_todos(
    todos: list[Todo], selected: int, key: Callable[..., str]
) -> tuple[list[Todo], int]:
    selected_todo = todos[selected]
    sorted_todos = []
    for section in sorted(get_indented_sections(todos), key=key):
        for todo in section:
            sorted_todos.append(todo)
    return sorted_todos, sorted_todos.index(selected_todo)


def sorting_methods() -> dict[str, Callable[..., int | str]]:
    return {
        "Alphabetical": lambda top_level_todo: top_level_todo[0].display_text,
        "Color": lambda top_level_todo: top_level_todo[0].color,
    }


def sort_by(
    method: str, todos: list[Todo], selected: Cursor, history: UndoRedo
) -> tuple[list[Todo], int]:
    history.add_undo(reset_todos, todos)
    if method in sorting_methods():
        return history.do(
            flatten_todos,
            todos,
            int(selected),
            sorting_methods()[method],
        )
    return todos, int(selected)


def sort_menu(
    parent_win: Any, todos: list[Todo], selected: Cursor, history: UndoRedo
) -> tuple[list[Todo], int]:
    parent_win.clear()
    set_header(parent_win, "Sort by:")
    lines = list(sorting_methods().keys())
    win = curses.newwin(
        len(lines) + 2,
        len(lines[0]) + 2,
        1,
        (parent_win.getmaxyx()[1] - (len(max(lines, key=len)) + 1)) // 2,
    )
    win.box()
    cursor = 0
    while True:
        parent_win.refresh()
        for i, v in enumerate(lines):
            win.addstr(
                i + 1,
                1,
                v,
                curses.A_REVERSE if i == cursor else 0,
            )
        try:
            key = win.getch()
        except KeyboardInterrupt:
            return todos, cursor
        if key == 107:  # k
            cursor -= 1
        elif key == 106:  # j
            cursor += 1
        elif key == 103:  # g
            cursor = 0
        elif key == 71:  # G
            cursor = len(lines)
        elif key in (113, 27):  # q | esc
            return todos, cursor
        elif key == 10:  # enter
            return sort_by(lines[cursor], todos, selected, history)
        else:
            continue
        cursor = clamp(cursor, 0, len(lines))
        parent_win.refresh()
        win.refresh()


def make_printable_sublist(
    height: int, lst: list[T], cursor: int, distance: int = -1
) -> tuple[list[T], int]:
    if len(lst) < height:
        return lst, cursor
    distance = height * 3 // 7 if distance < 0 else distance
    start = max(0, cursor - distance)
    end = min(len(lst), start + height)
    # If len(sublist) < height, stop moving list and resume moving cursor
    if end - start < height:
        start = len(lst) - height
        end = len(lst)
    return lst[start:end], cursor - start


def print_todos(win: Any, todos: list[Todo], selected: Cursor) -> None:
    if win is None:
        from os import get_terminal_size

        width, height = get_terminal_size()
    else:
        height, width = win.getmaxyx()
    new_todos, temp_selected = make_printable_sublist(height - 1, todos, int(selected))
    highlight = range(temp_selected, len(selected) + temp_selected)
    for relative, (i, v) in zip(
        [*range(temp_selected - 1, -1, -1), int(selected), *range(0, len(new_todos))],
        enumerate(new_todos),
    ):
        if v.color is None:
            raise ValueError(f"Invalid color for `{v}`")
        display_string = (
            "".join(
                [
                    v.indent_level * " ",
                    f"{v.get_box()}",
                    (
                        f"{get_bullet(v.indent_level)} "
                        if not v.has_box() and BULLETS
                        else ""
                    ),
                    (
                        f"{todos.index(v) + 1}. "
                        if ENUMERATE and not RELATIVE_ENUMERATE
                        else ""
                    ),
                    f"{relative + 1}. " if RELATIVE_ENUMERATE else "",
                    (
                        strikethrough(v.display_text)
                        if v.is_toggled()
                        else v.display_text
                    ),
                ]
            )
            if i not in highlight or not v.is_empty()
            else "⎯" * 8
        )[: width - 1].ljust(width - 1, " ")
        counter = 0
        if win is None:
            print(
                {
                    1: "\u001b[31m",
                    2: "\u001b[32m",
                    3: "\u001b[33m",
                    4: "\u001b[34m",
                    5: "\u001b[35m",
                    6: "\u001b[36m",
                    7: "\u001b[37m",
                }[v.color]
                + display_string
                + "\u001b[0m"
            )
            continue
        while counter < len(display_string) - 1:
            try:
                win.addch(
                    i + 1,
                    counter,
                    display_string[counter],
                    curses.color_pair(v.color or get_color("White"))
                    | (curses.A_REVERSE if i in highlight else 0),
                )
            except OverflowError:
                """
                This function call will throw an OverflowError if
                the terminal doesn't support the box character as it
                is technically a wide character. By `continue`-ing,
                we don't print the box character and indirectly
                prompt the user to use the -x option and use simple
                boxes when printing.
                """
                counter += 1
                continue
            counter += 1


def get_bullet(indentation_level: int) -> str:
    symbols = [
        "•",
        "◦",
        "▪",
        # "▫",
    ]
    return symbols[indentation_level // INDENT % len(symbols)]


def todo_from_clipboard(
    todos: list[Todo], selected: int, copied_todo: Todo
) -> list[Todo]:
    try:
        from pyperclip import paste
    except ModuleNotFoundError:
        raise ExternalModuleNotFoundError("pyperclip", todos, "paste")
    todo = paste()
    if copied_todo.display_text == todo:
        todos.insert(selected + 1, Todo(copied_todo.text))
        return todos
    if "\n" in todo:
        return todos
    todos.insert(selected + 1, Todo(f"- {todo}"))
    return todos


def cursor_up(selected: int, len_todos: int) -> int:
    return clamp(selected - 1, 0, len_todos)


def cursor_down(selected: int, len_todos: int) -> int:
    return clamp(selected + 1, 0, len_todos)


def cursor_top(len_todos: int) -> int:
    return clamp(0, 0, len_todos)


def cursor_bottom(len_todos: int) -> int:
    return clamp(len_todos, 0, len_todos)


def cursor_to(position: int, len_todos: int) -> int:
    return clamp(position, 0, len_todos)


def todo_up(todos: list[Todo], selected: int) -> tuple[list[Todo], int]:
    todos = swap_todos(todos, selected, selected - 1)
    update_file(FILENAME, todos)
    return todos, cursor_up(selected, len(todos))


def todo_down(todos: list[Todo], selected: int) -> tuple[list[Todo], int]:
    todos = swap_todos(todos, selected, selected + 1)
    update_file(FILENAME, todos)
    return todos, cursor_down(selected, len(todos))


def new_todo_next(
    stdscr: Any,
    todos: list[Todo],
    selected: int,
    mode: Mode | None = None,
    paste: bool = False,
    copied_todo: Todo | None = None,
) -> tuple[list[Todo], int]:
    temp = todos.copy()
    todos = (
        insert_todo(
            stdscr,
            todos,
            selected + 1,
            mode,
        )
        if not paste
        else todo_from_clipboard(
            todos, selected, copied_todo if copied_todo is not None else Todo()
        )
    )
    stdscr.clear()
    if temp != todos:
        selected = cursor_down(selected, len(todos))
    update_file(FILENAME, todos)
    return todos, selected


def new_todo_current(stdscr: Any, todos: list[Todo], selected: int) -> list[Todo]:
    todos = insert_todo(stdscr, todos, selected)
    stdscr.clear()
    update_file(FILENAME, todos)
    return todos


def delete_todo(
    stdscr: Any, todos: list[Todo], selected: Cursor
) -> tuple[list[Todo], int]:
    positions = selected.get_deletable()
    selected.set_to(clamp(int(selected), 0, len(todos) - 1))
    for pos in positions:
        todos = remove_todo(todos, pos)
    stdscr.clear()
    update_file(FILENAME, todos)
    return todos, int(selected)


def color_todo(stdscr: Any, todos: list[Todo], selected: Cursor) -> list[Todo]:
    new_color = color_menu(stdscr, todos[int(selected)].color)
    for pos in selected.positions:
        todos[pos].set_color(new_color)
    stdscr.clear()
    update_file(FILENAME, todos)
    return todos


def edit_todo(stdscr: Any, todos: list[Todo], selected: int) -> list[Todo]:
    y, x = stdscr.getmaxyx()
    todo = todos[selected].display_text
    ncols = max(x * 3 // 4, len(todo) + 3) if len(todo) < x - 1 else x * 3 // 4
    begin_x = x // 8 if len(todo) < x - 1 - ncols else (x - ncols) // 2
    edited_todo = wgetnstr(
        stdscr,
        curses.newwin(3, ncols, y // 2 - 3, begin_x),
        todo=todos[selected],
        prev_todo=Todo(),
    )
    if edited_todo.is_empty():
        return todos
    todos[selected] = edited_todo
    stdscr.clear()
    update_file(FILENAME, todos)
    return todos


def copy_todo(todos: list[Todo], selected: int, copied_todo: Todo) -> None:
    try:
        from pyperclip import copy
    except ModuleNotFoundError:
        raise ExternalModuleNotFoundError("pyperclip", todos, "copy")
    copy(todos[selected].display_text)
    copied_todo.call_init(todos[selected].text)


def paste_todo(
    stdscr: Any, todos: list[Todo], selected: int, copied_todo: Todo
) -> tuple[list[Todo], int]:
    return new_todo_next(stdscr, todos, selected, paste=True, copied_todo=copied_todo)


def blank_todo(todos: list[Todo], selected: int) -> tuple[list[Todo], int]:
    insert_empty_todo(todos, selected + 1)
    selected = cursor_down(selected, len(todos))
    update_file(FILENAME, todos)
    return todos, selected


def toggle(todos: list[Todo], selected: Cursor) -> list[Todo]:
    for pos in selected.positions:
        todos[pos].toggle()
    update_file(FILENAME, todos)
    return todos


def quit_program(todos: list[Todo]) -> int:
    if is_file_externally_updated(FILENAME, todos):
        todos = validate_file(read_file(FILENAME))
    return update_file(FILENAME, todos, True)


def reset_todos(todos: list[Todo]) -> list[Todo]:
    return todos.copy()


def relative_cursor_to(
    win: Any, history: UndoRedo, todos: list[Todo], selected: int, first_digit: int
) -> int:
    total = str(first_digit)
    while True:
        try:
            key = win.getch()
        except KeyboardInterrupt:  # exit on ^C
            return selected
        if key in (259, 107):  # up | k
            history.add_undo(cursor_to, selected, len(todos))
            return history.do(cursor_to, selected - int(total), len(todos))
        elif key in (258, 106):  # down | j
            history.add_undo(cursor_to, selected, len(todos))
            return history.do(cursor_to, selected + int(total), len(todos))
        elif key in (103, 71):  # g | G
            history.add_undo(cursor_to, selected, len(todos))
            return history.do(cursor_to, int(total) - 1, len(todos))
        elif key in range(48, 58):  # digits
            total += str(key - 48)
            continue
        return selected


def indent(todos: list[Todo], selected: Cursor) -> tuple[list[Todo], int]:
    for pos in selected.positions:
        todos[pos].indent()
    update_file(FILENAME, todos)
    return todos, selected.positions[0]


def dedent(todos: list[Todo], selected: Cursor) -> tuple[list[Todo], int]:
    for pos in selected.positions:
        todos[pos].dedent()
    update_file(FILENAME, todos)
    return todos, selected.positions[0]


def toggle_todo_note(todos: list[Todo], selected: Cursor) -> None:
    for pos in selected.positions:
        todo = todos[pos]
        todo.box_char = None if todo.has_box() else "-"
    update_file(FILENAME, todos)


def init() -> None:
    curses.use_default_colors()
    curses.curs_set(0)
    for i, v in enumerate(
        [
            curses.COLOR_RED,
            curses.COLOR_GREEN,
            curses.COLOR_YELLOW,
            curses.COLOR_BLUE,
            curses.COLOR_MAGENTA,
            curses.COLOR_CYAN,
            curses.COLOR_WHITE,
        ],
        start=1,
    ):
        curses.init_pair(i, v, -1)


def main(stdscr: Any, header: str) -> int:
    init()
    todos = validate_file(read_file(FILENAME))
    selected = Cursor(0)
    history = UndoRedo()
    mode = Mode(True)
    copied_todo = Todo("- placeholder")

    while True:
        if AUTOSAVE and is_file_externally_updated(FILENAME, todos):
            todos = validate_file(read_file(FILENAME))
        set_header(stdscr, f"{header}:")
        print_todos(stdscr, todos, selected)
        stdscr.refresh()
        if not mode.toggle_mode:
            todos = selected.todo_set_to(
                history.do(new_todo_next, stdscr, todos, int(selected), mode)
            )
            history.add_undo(delete_todo, stdscr, todos, selected)
            continue
        try:
            key = stdscr.getch()
        except KeyboardInterrupt:  # exit on ^C
            return quit_program(todos)
        if key == 113:  # q
            return quit_program(todos)
        elif key in (259, 107):  # up | k
            history.add_undo(cursor_to, int(selected), len(todos))
            selected.set_to(history.do(cursor_up, int(selected), len(todos)))
        elif key in (258, 106):  # down | j
            history.add_undo(cursor_to, int(selected), len(todos))
            selected.set_to(history.do(cursor_down, int(selected), len(todos)))
        elif key == 75:  # K
            selected.multiselect_up()
        elif key == 74:  # J
            selected.multiselect_down(len(todos))
        elif key == 111:  # o
            todos = selected.todo_set_to(
                history.do(new_todo_next, stdscr, todos, int(selected))
            )
            history.add_undo(delete_todo, stdscr, todos, selected)
        elif key == 79:  # O
            todos = history.do(new_todo_current, stdscr, todos, int(selected))
            history.add_undo(delete_todo, stdscr, todos, selected)
        elif key == 100:  # d
            history.add_undo(lambda a, b: (a, b), todos, int(selected))
            todos = selected.todo_set_to(
                history.do(delete_todo, stdscr, todos, selected)
            )
        elif key == 117:  # u
            todos = selected.todo_set_to(
                history.handle_return(history.undo, todos, int(selected))
            )
            update_file(FILENAME, todos)
        elif key == 18:  # ^R
            continue  # redo doesn't work right now
            todos = selected.todo_set_to(
                history.handle_return(history.redo, todos, int(selected))
            )
            update_file(FILENAME, todos)
        elif key == 99:  # c
            # TODO: not currently undoable (color to previous state)
            todos = color_todo(stdscr, todos, selected)
        elif key == 105:  # i
            if len(todos) <= 0:
                continue
            history.add_undo(reset_todos, todos)
            todos = history.do(edit_todo, stdscr, todos, int(selected))
        elif key == 103:  # g
            history.add_undo(cursor_to, int(selected), len(todos))
            selected.set_to(history.do(cursor_top, len(todos)))
        elif key == 71:  # G
            history.add_undo(cursor_to, int(selected), len(todos))
            selected.set_to(history.do(cursor_bottom, len(todos)))
        elif key == 121:  # y
            # TODO: not currently undoable (copy previous item in clipboard)
            copy_todo(todos, int(selected), copied_todo)
        elif key == 112:  # p
            todos = selected.todo_set_to(
                history.do(paste_todo, stdscr, todos, int(selected), copied_todo)
            )
            history.add_undo(delete_todo, stdscr, todos, selected)
        elif key == 45:  # -
            todos = selected.todo_set_to(history.do(blank_todo, todos, int(selected)))
            history.add_undo(delete_todo, stdscr, todos, selected)
        elif key == 104:  # h
            help_menu(stdscr)
        elif key == 98:  # b
            magnify(stdscr, todos, selected)
        elif key == 27:  # any escape sequence
            stdscr.nodelay(True)
            subch = stdscr.getch()
            stdscr.nodelay(False)
            if subch == -1:  # escape, otherwise skip `[`
                return quit_program(todos)
            elif subch == 106:  # alt + j
                history.add_undo(todo_up, todos, int(selected) + 1)
                todos = selected.todo_set_to(
                    history.do(todo_down, todos, int(selected))
                )
            elif subch == 107:  # alt + k
                history.add_undo(todo_down, todos, int(selected) - 1)
                todos = selected.todo_set_to(history.do(todo_up, todos, int(selected)))
            elif subch == 103:  # alt + g
                selected.multiselect_top()
            elif subch == 71:  # alt + G
                selected.multiselect_bottom(len(todos))
            elif subch in range(48, 58):  # digits:
                selected.multiselect_from(stdscr, subch - 48, len(todos))
        elif key == 426:  # alt + j (on windows)
            history.add_undo(todo_up, todos, int(selected) + 1)
            todos = selected.todo_set_to(history.do(todo_down, todos, int(selected)))
        elif key == 427:  # alt + k (on windows)
            history.add_undo(todo_down, todos, int(selected) - 1)
            todos = selected.todo_set_to(history.do(todo_up, todos, int(selected)))
        elif key == 9:  # tab
            history.add_undo(reset_todos, todos)
            todos = selected.todo_set_to(history.do(indent, todos, selected))
        elif key in (351, 353):  # shift + tab
            history.add_undo(reset_todos, todos)
            todos = selected.todo_set_to(history.do(dedent, todos, selected))
        elif key == 47:  # /
            search(stdscr, todos, selected)
        elif key in (24, 11):  # ctrl + x/k
            mode.toggle()
        elif key == 330:  # delete
            history.do(toggle_todo_note, todos, selected)
            history.add_undo(toggle_todo_note, todos, selected)
        elif key == 115:  # s
            todos = selected.todo_set_to(sort_menu(stdscr, todos, selected, history))
        elif key == 10:  # enter
            todos = history.do(toggle, todos, selected)
            history.add_undo(toggle, todos, selected)
        elif key in range(48, 58):  # digits
            selected.set_to(
                relative_cursor_to(stdscr, history, todos, int(selected), key - 48)
            )
        else:
            continue


if __name__ == "__main__":
    handle_args(get_args())
    if NO_GUI:
        print(f"{HEADER}:")
        print_todos(None, validate_file(read_file(FILENAME)), Cursor(0))
        exit()
    curses.wrapper(main, header=HEADER)
