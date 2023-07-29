#!/usr/bin/env python3
# pyright: reportMissingImports=false

import curses
from pathlib import Path
from typing import List
import re

STRIKETHROUGH = False
FILESTRING = "todo.txt"
FILENAME = Path(FILESTRING)
HELP_FILE = Path(__file__).parent.joinpath("README.md").absolute()
AUTOSAVE = True
HEADER = ""
INDENT = 2
ENUMERATE = False

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
    def _init_color_dtext(self):
        counter = self.indent_level
        while True:
            if self._text[counter] == " ":
                return (
                    7
                    if self._text[counter - 1] == "-"
                    else int(self._text[counter - 1])
                ), self._text[counter:].lstrip()
            counter += 1

    def __init__(self, text):
        self._text = str(text)
        self.indent_level = len(text) - len(text.lstrip())
        self.box_char = self._text[self.indent_level]
        self.color, self.display_text = self._init_color_dtext()

    def __getitem__(self, key):
        return self._text[key]

    def set_display_text(self, display_text):
        self.display_text = display_text
        self._text = repr(self)

    def is_toggled(self):
        return self.box_char == "+"

    def set_color(self, color):
        self.color = color

    def get_box(self):
        table = {
            "+": "☑",
            "-": "☐",
        }

        if self.box_char in table:
            return table[self.box_char]
        raise KeyError(
            f"The completion indicator of `{self._text}` is not one of (+, -)"
        )

    def toggle(self):
        new_box = {"+": "-", "-": "+"}[self.box_char]
        self.box_char = new_box
        self._text = repr(self)

    def indent(self):
        self.indent_level += INDENT
        self._text = repr(self)

    def dedent(self):
        if self.indent_level >= INDENT:
            self.indent_level -= INDENT
            self._text = repr(self)

    def to_note(self):
        self.__class__ = Note(self._text).__class__

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return (
            f"{self.indent_level * ' '}{self.box_char}{self.color} {self.display_text}"
        )


class EmptyTodo(Todo):
    def __init__(self):
        self.display_text = ""
        self.color = 7
        self.indent_level = 0

    def is_toggled(self):
        return False

    def toggle(self):
        return

    def set_display_text(self, text):
        self.box_char = "-"
        self.display_text = text
        self._text = f"{self.box_char}{self.color} {text}"
        self.__class__ = Todo(self._text).__class__

    def get_box(self):
        return " "

    def __repr__(self):
        return self.display_text


class Note(Todo):
    def _init_color_dtext(self):
        if not self._text[self.indent_level].isdigit():
            return 7, self._text
        return (
            int(self._text[self.indent_level]),
            self._text[self.indent_level + 2 :],
        )

    def __init__(self, text):
        self._text = text
        self.indent_level = len(text) - len(text.lstrip())
        self.color, self.display_text = self._init_color_dtext()

    def is_toggled(self):
        return False

    def toggle(self):
        return

    def to_todo(self):
        self.box_char = "-"
        self._text = (
            f"{self.indent_level * ' '}{self.box_char}{self.color} {self.display_text}"
        )
        self.__class__ = Todo(self._text).__class__

    def __repr__(self):
        if self.color == 7:
            return f"{self.indent_level * ' '}{self.display_text}"
        return f"{self.indent_level * ' '}{self.color} {self.display_text}"


class UndoRedo:
    def __init__(self):
        self.history = []
        self.redos = []
        self.index = -1

    def handle_return(self, undo_or_redo, todos: list, selected: int):
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

    def undo(self, todos, selected):
        if self.index < 0:
            return todos, selected
        func, args = self.history[self.index]
        self.index -= 1
        return func(*args)

    def redo(self, todos, selected):
        if self.index >= len(self.history) - 1:
            return todos, selected
        self.index += 1
        func, args = self.redos[self.index]
        return func(*args)

    def add_undo(self, revert_with, *args):
        self.history.append((revert_with, deepcopy_ignore(args)))
        self.index = len(self.history) - 1

    def do(self, func, *args):
        # TODO: implement redo
        # I have the redo function and the
        # args it needs... how should I store it?
        # self.redos.append((func, deepcopy_ignore(args).append(args[1][args[2]])
        # if func.__name__ == "new_todo_next" else deepcopy_ignore(args)))
        return func(*args)

    def __repr__(self):
        return "\n".join(f"{i[0].__name__}: {i[1]}" for i in self.history)


class Cursor:
    def __init__(self, position, *positions):
        self.positions = [position, *positions]

    def __len__(self):
        return len(self.positions)

    def __str__(self):
        return str(self.positions[0])

    def __int__(self):
        return self.positions[0]

    def __contains__(self, child):
        return child in self.positions

    def set_to(self, position):
        self.positions = [position]

    def todo_set_to(self, todo_position):
        self.positions[0] = todo_position[1]
        return todo_position[0]

    def set_multiple(self, positions):
        self.positions = positions

    def select_next(self):
        self.positions.append(max(self.positions) + 1)
        self.positions.sort()

    def deselect_next(self):
        if len(self.positions) > 1:
            self.positions.remove(max(self.positions))

    def deselect_prev(self):
        if len(self.positions) > 1:
            self.positions.remove(min(self.positions))

    def select_prev(self):
        self.positions.append(min(self.positions) - 1)
        self.positions.sort()

    def get_deletable(self):
        return [min(self.positions) for _ in self.positions]

    def multiselect_down(self, max_len):
        if max(self.positions) >= max_len - 1:
            return
        if len(self.positions) == 1 or self.direction == "down":
            self.select_next()
            self.direction = "down"
            return
        self.deselect_prev()

    def multiselect_up(self):
        if min(self.positions) == 0 and self.direction == "up":
            return
        if len(self.positions) == 1 or self.direction == "up":
            self.select_prev()
            self.direction = "up"
            return
        self.deselect_next()


class Mode:
    def __init__(self, toggle_mode):
        self.toggle_mode = toggle_mode

    def toggle(self):
        self.toggle_mode = not self.toggle_mode


class ExternalModuleNotFoundError(Exception):
    def __init__(self, module, todos, operation):
        update_file(FILENAME, todos, True)
        exit(
            f"`{module}` module required for {operation} operation. "
            f"Try `pip install {module}`"
        )


def read_file(filename: Path):
    if not filename.exists():
        with filename.open("w") as f:
            return ""
    with filename.open() as f:
        return f.read()


def validate_file(raw_data):
    if len(raw_data) == 0:
        return []
    usable_data = []
    for line in raw_data.split("\n"):
        if len(line) == 0:
            usable_data.append(EmptyTodo())
        elif re.match(r"^( *)?(\+|-)\d? .*$", line):
            usable_data.append(Todo(line))
        elif re.match(r"^( *\d )?.*$", line):
            usable_data.append(Note(line))
        else:
            raise ValueError(f"Invalid todo: {line}")
    return usable_data


def get_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Ndo is a todo list program to help you manage your todo lists",
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Controls:\n  "
        + "\n  ".join(md_table_to_lines(43, 66, str(HELP_FILE), ["<kbd>", "</kbd>"])),
    )
    parser.add_argument(
        "--help",
        "-h",
        action="help",
        help="Show this help message and exit.",
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
        "--enumerate",
        "-e",
        action="store_true",
        default=ENUMERATE,
        help=f"Boolean: determines if todos are numbered when\
            printed or not. Default is `{ENUMERATE}`.",
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
        default=HEADER,
        help=f"Allows passing alternate header.\
            Make sure to quote multi-word headers.\
            Default is filename.",
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
    return parser.parse_args()


def handle_args(args):
    global AUTOSAVE, FILENAME, HELP_FILE, STRIKETHROUGH, HEADER, INDENT, ENUMERATE
    AUTOSAVE = args.autosave
    INDENT = args.indentation_level
    FILENAME = Path(args.filename)
    HELP_FILE = Path(args.help_file)
    STRIKETHROUGH = args.strikethrough
    HEADER = FILENAME.name if args.title == HEADER else args.title
    ENUMERATE = args.enumerate


def deepcopy_ignore(lst):
    from _curses import window as curses_window
    from copy import deepcopy

    return [i if isinstance(i, curses_window) else deepcopy(i) for i in lst]


def clamp(counter: int, minimum: int, maximum: int):
    return min(max(counter, minimum), maximum - 1)


def update_file(filename, lst, save=AUTOSAVE):
    if not save:
        return 0
    with filename.open("w") as f:
        return f.write("\n".join(map(repr, lst)))


def print(message, end="\n"):
    with open("debugging/log.txt", "a") as f:
        f.write(f"{message}{end}")


def wgetnstr(win, mode=None, n=1024, chars="", cursor="█", current_todo=None):
    """
    Reads a string from the given window with max chars n\
    and initial chars chars. Returns a string from the user\
    Functions like a JavaScript alert box for user input.

    Args:
        win (Window object):
            The window to read from. The entire window\
            will be used, so a curses.newwin() should be\
            generated specifically for use with this\
            function. As a box will be created around the\
            window's border, the window must have a minimum\
            height of 3 characters. The width will determine\
            a maximum value of n.
        n (int, optional):
            Max number of characters in the read string.\
            It might error if this number is greater than\
            the area of the window. Defaults to 1024.
        chars (str, optional):
            Initial string to occupy the window.\
            Defaults to "" (empty string).
        cursor (str, optional):
            Cursor character to display while typing.\
            Defaults to "█".

    Returns:
        str: Similar to the built in input() function,\
        returns a string of what the user entered.
    """
    if win.getmaxyx()[0] < 3:
        raise ValueError(
            "Window is too short, it won't be able to display the minimum 1 line of text."
        )
    elif win.getmaxyx()[0] > 3:
        raise NotImplementedError("Multiline text editing is not supported")
    original = chars
    chars = list(chars)
    position = len(chars)
    win.box()
    win.nodelay(False)
    while True:
        if position == len(chars):
            if len(chars) + 1 >= win.getmaxyx()[1] - 1:
                return "".join(chars)
            win.addstr(1, len(chars) + 1, cursor)
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
                return "".join(chars)
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
            current_todo.indent()
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
                current_todo.dedent()
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

    return "".join(chars)


def hline(win, y, x, ch, n):
    win.addch(y, x, curses.ACS_LTEE)
    win.hline(y, x + 1, ch, n - 2)
    win.addch(y, x + n - 1, curses.ACS_RTEE)


def insert_todo(stdscr, todos: list, index: int, mode=None):
    y, x = stdscr.getmaxyx()
    if (
        todo := wgetnstr(
            curses.newwin(3, x * 3 // 4, y // 2 - 3, x // 8),
            mode=mode,
            current_todo=todos[index],
        )
    ) == "":
        return todos
    if todos[index].indent_level != 0:
        indent_level = todos[index].indent_level
    else:
        indent_level = todos[index - 1].indent_level if len(todos) > 0 else 0
    todos.insert(index, Todo(f"{' ' * indent_level}- {todo}"))
    return todos


def insert_empty_todo(todos, index):
    todos.insert(index, EmptyTodo())
    return todos


def search(stdscr, todos, selected):
    set_header(stdscr, "Searching...")
    stdscr.refresh()
    y, x = stdscr.getmaxyx()
    sequence = wgetnstr(curses.newwin(3, x * 3 // 4, y // 2 - 3, x // 8))
    stdscr.clear()
    for i, todo in enumerate(todos[int(selected) :], start=int(selected)):
        if sequence in todo.display_text:
            break
    else:
        selected.set_to(0)
        return
    selected.set_to(i)


def set_header(stdscr, message):
    stdscr.addstr(0, 0, message, curses.A_BOLD)


def remove_todo(todos: list, index):
    if len(todos) < 1:
        return todos
    todos.pop(index)
    return todos


def strikethrough(text):
    return "\u0336".join(text) if STRIKETHROUGH else text


def swap_todos(todos: list, idx1, idx2):
    if min(idx1, idx2) >= 0 and max(idx1, idx2) < len(todos):
        todos[idx1], todos[idx2] = todos[idx2], todos[idx1]
    return todos


def md_table_to_lines(
    first_line_idx: int,
    last_line_idx: int,
    filename: str = "README.md",
    remove: List[str] = [],
) -> List[str]:
    """
    Converts a markdown table to a list of formatted strings.

    Args:
        first_line_idx (int): The index of the first line of the markdown table to be converted.
        last_line_idx (int): The index of the last line of the markdown table to be converted.
        filename (str, optional): The name of the markdown file containing the table. Default is "README.md".
        remove (list[str], optional): The list of strings to be removed from each line.
        This is in the case of formatting that should exist in markdown but not python. Default is an empty list.

    Returns:
        list[str]: A list of formatted strings representing the converted markdown table.

    Raises:
        ValueError: If the last line index is less than or equal to the first line index.
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
    for i, _ in enumerate(lines):
        for item in remove:
            lines[i] = lines[i].replace(item, "")
        lines[i] = lines[i].split("|")[1:-1]
    column_count = len(lines[0])
    lines[1] = ["-" for _ in range(column_count)]

    # Create lists of columns
    columns = [[0, []] for _ in range(column_count)]
    for i in range(column_count):
        for line in lines:
            columns[i][1].append(line[i])

    # Find the maximum length of each column
    for i, (_, v) in enumerate(columns):
        columns[i][0] = len(max([w.strip() for w in v], key=len))
    lines[1] = ["-" * (l + 1) for l, _ in columns]

    # Join the lines together into a list of formatted strings
    for i, line in enumerate(lines):
        for j, v in enumerate(line):
            line[j] = v.strip().ljust(columns[j][0] + 2)
        lines[i] = "".join(lines[i])
    lines[1] = "-" * (
        sum(columns[i][0] for i, _ in enumerate(columns)) + 2 * (len(columns) - 1)
    )
    return lines


def help_menu(parent_win):
    parent_win.clear()
    set_header(parent_win, "Help (k/j to scroll):")
    lines = []
    for i in md_table_to_lines(
        43, 66, str(HELP_FILE), ["<kbd>", "</kbd>", "(arranged alphabetically)"]
    ):
        lines.append(i[:-2])
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


def magnify(stdscr, todos, selected):
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


def get_color(color):
    return COLORS[color]


def color_menu(parent_win, original: int):
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


def make_printable_sublist(height: int, lst: list, cursor: int, distance: int = -1):
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


def print_todos(win, todos, selected):
    height, width = win.getmaxyx()
    new_todos, temp_selected = make_printable_sublist(height - 1, todos, int(selected))
    highlight = range(temp_selected, len(selected) + temp_selected)
    for i, v in enumerate(new_todos):
        if v.color is None:
            raise ValueError(f"Invalid color for `{v}`")
        display_string = (
            "".join(
                [
                    v.indent_level * " ",
                    "" if isinstance(v, Note) else f"{v.get_box()}  ",
                    f"{i + 1}. " if ENUMERATE else "",
                    (
                        strikethrough(v.display_text)
                        if v.is_toggled()
                        else v.display_text
                    ),
                ]
            )
            if i not in highlight or not isinstance(v, EmptyTodo)
            else "⎯" * 8
        )[: width - 1].ljust(width - 1, " ")
        counter = 0
        while counter < len(display_string):
            win.addch(
                i + 1,
                counter,
                display_string[counter],
                curses.color_pair(v.color or get_color("White"))
                | (curses.A_REVERSE if i in highlight else 0),
            )
            counter += 1


def todo_from_clipboard(todos: list, selected: int):
    try:
        from pyperclip import paste
    except ModuleNotFoundError:
        raise ExternalModuleNotFoundError("pyperclip", todos, "paste")
    todo = paste()
    if "\n" in todo:
        return todos
    todos.insert(selected + 1, Todo(f"- {todo}"))
    return todos


def cursor_up(selected, len_todos):
    return clamp(selected - 1, 0, len_todos)


def cursor_down(selected, len_todos):
    return clamp(selected + 1, 0, len_todos)


def cursor_top(len_todos):
    return clamp(0, 0, len_todos)


def cursor_bottom(len_todos):
    return clamp(len_todos, 0, len_todos)


def cursor_to(position, len_todos):
    return clamp(position, 0, len_todos)


def todo_up(stdscr, todos, selected):
    todos = swap_todos(todos, selected, selected - 1)
    update_file(FILENAME, todos)
    return todos, cursor_up(selected, len(todos))


def todo_down(stdscr, todos, selected):
    todos = swap_todos(todos, selected, selected + 1)
    update_file(FILENAME, todos)
    return todos, cursor_down(selected, len(todos))


def new_todo_next(stdscr, todos: list, selected: int, mode=None, paste: bool = False):
    temp = todos.copy()
    todos = (
        insert_todo(
            stdscr,
            todos,
            selected + 1,
            mode,
        )
        if not paste
        else todo_from_clipboard(todos, selected)
    )
    stdscr.clear()
    if temp != todos:
        selected = cursor_down(selected, len(todos))
    update_file(FILENAME, todos)
    return todos, selected


def new_todo_current(stdscr, todos, selected):
    todos = insert_todo(stdscr, todos, selected)
    stdscr.clear()
    update_file(FILENAME, todos)
    return todos


def delete_todo(stdscr, todos, selected):
    if isinstance(selected, Cursor):
        positions = selected.get_deletable()
        selected.set_to(cursor_up(int(selected), len(todos)))
    elif isinstance(selected, int):
        positions = [selected]
    for pos in positions:
        todos = remove_todo(todos, pos)
    stdscr.clear()
    update_file(FILENAME, todos)
    return todos, int(selected)


def color_todo(stdscr, todos, selected):
    new_color = color_menu(stdscr, todos[int(selected)].color)
    for pos in selected.positions:
        todos[pos].set_color(new_color)
    stdscr.clear()
    update_file(FILENAME, todos)
    return todos


def edit_todo(stdscr, todos, selected):
    y, x = stdscr.getmaxyx()
    todo = todos[selected].display_text
    ncols = max(x * 3 // 4, len(todo) + 3) if len(todo) < x - 1 else x * 3 // 4
    begin_x = x // 8 if len(todo) < x - 1 - ncols else (x - ncols) // 2
    if (
        edited_todo := wgetnstr(
            curses.newwin(3, ncols, y // 2 - 3, begin_x),
            chars=todo,
            current_todo=todos[selected],
        )
    ) == "":
        return todos
    todos[selected].set_display_text(edited_todo)
    stdscr.clear()
    update_file(FILENAME, todos)
    return todos


def copy_todo(todos, selected):
    try:
        from pyperclip import copy
    except ModuleNotFoundError:
        raise ExternalModuleNotFoundError("pyperclip", todos, "copy")
    copy(todos[selected].display_text)


def paste_todo(stdscr, todos, selected):
    return new_todo_next(stdscr, todos, selected, paste=True)


def blank_todo(stdscr, todos, selected):
    insert_empty_todo(todos, selected + 1)
    selected = cursor_down(selected, len(todos))
    update_file(FILENAME, todos)
    return todos, selected


def toggle(todos, selected):
    for pos in selected.positions:
        todos[pos].toggle()
    update_file(FILENAME, todos)
    return todos


def quit_program(todos):
    return update_file(FILENAME, todos, True)


def reset_todos(todos: list):
    return todos.copy()


def relative_cursor_to(
    win, history: UndoRedo, todos: list, selected: int, first_digit: int
):
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
        elif key in range(48, 58):  # digits
            total += str(key - 48)
            continue
        return selected


def indent(todos, selected):
    for pos in selected.positions:
        todos[pos].indent()
    update_file(FILENAME, todos)
    return todos, selected.positions[0]


def dedent(todos, selected):
    for pos in selected.positions:
        todos[pos].dedent()
    update_file(FILENAME, todos)
    return todos, selected.positions[0]


def init():
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


def main(stdscr, header):
    init()
    todos = validate_file(read_file(FILENAME))
    selected = Cursor(0)
    history = UndoRedo()
    mode = Mode(True)

    while True:
        set_header(stdscr, f"{header}:")
        print_todos(stdscr, todos, selected)
        stdscr.refresh()
        if not mode.toggle_mode:
            todos = selected.todo_set_to(
                history.do(new_todo_next, stdscr, todos, int(selected), mode)
            )
            history.add_undo(delete_todo, stdscr, todos, int(selected))
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
            history.add_undo(todo_down, stdscr, todos, int(selected) - 1)
            todos = selected.todo_set_to(
                history.do(todo_up, stdscr, todos, int(selected))
            )
        elif key == 74:  # J
            history.add_undo(todo_up, stdscr, todos, int(selected) + 1)
            todos = selected.todo_set_to(
                history.do(todo_down, stdscr, todos, int(selected))
            )
        elif key == 111:  # o
            todos = selected.todo_set_to(
                history.do(new_todo_next, stdscr, todos, int(selected))
            )
            history.add_undo(delete_todo, stdscr, todos, int(selected))
        elif key == 79:  # O
            todos = history.do(new_todo_current, stdscr, todos, int(selected))
            history.add_undo(delete_todo, stdscr, todos, int(selected))
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
            copy_todo(todos, int(selected))
        elif key == 112:  # p
            todos = selected.todo_set_to(
                history.do(paste_todo, stdscr, todos, int(selected))
            )
            history.add_undo(delete_todo, stdscr, todos, int(selected))
        elif key == 45:  # -
            todos = selected.todo_set_to(
                history.do(blank_todo, stdscr, todos, int(selected))
            )
            history.add_undo(delete_todo, stdscr, todos, int(selected))
        elif key == 104:  # h
            help_menu(stdscr)
        elif key == 98:  # b
            magnify(stdscr, todos, selected)
        elif key == 27:  # any escape sequence
            stdscr.nodelay(True)
            subch = stdscr.getch()
            if subch == -1:  # escape, otherwise skip `[`
                return quit_program(todos)
            elif subch == 106:  # alt + j
                selected.multiselect_down(len(todos))
            elif subch == 107:  # alt + k
                selected.multiselect_up()
            stdscr.nodelay(False)
        elif key == 426:  # alt + j (on windows)
            selected.multiselect_down(len(todos))
        elif key == 427:  # alt + k (on windows)
            selected.multiselect_up()
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
            for pos in selected.positions:
                if isinstance(todos[pos], Note):
                    todos[pos].to_todo()
                elif Todo is type(todos[pos]):
                    todos[pos].to_note()
            update_file(FILENAME, todos)
        elif key == 10:  # enter
            todos = history.do(toggle, todos, selected)
            history.add_undo(toggle, todos, selected)
        elif key in range(48, 58):  # digits
            selected.set_to(
                relative_cursor_to(stdscr, history, todos, int(selected), key - 48)
            )
        else:
            continue
        stdscr.refresh()


if __name__ == "__main__":
    handle_args(get_args())
    curses.wrapper(main, header=HEADER)
