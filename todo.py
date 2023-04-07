#!/usr/bin/env python3

import curses
import os

STRIKETHROUGH = False
FILENAME = f"{os.path.dirname(__file__)}/todo.txt"
HELP_FILE = f"{os.path.dirname(__file__)}/README.md"
AUTOSAVE = True
HEADER = "TODO"
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
    def _set_color(self, color):
        if str(color).isalpha():
            if len(self.text) - len(self.display_text) == 3:
                return int(self.text[1])
            return get_color(color)
        return color

    def __init__(self, text, color="White"):
        self.text = str(text)
        self.box_char = self.text[0]
        self.display_text = self.text.split(" ", 1)[1]
        self.color = self._set_color(color)

    def __getitem__(self, key):
        return self.text[key]

    def split(self, *a):
        return self.text.split(*a)

    def startswith(self, *a):
        return self.text.startswith(*a)

    def set_color(self, color):
        self.color = color if color not in (None, 0) else 7

    def get_box(self):
        table = {
            "+": "☑",
            "-": "☐",
        }

        if self.box_char in table:
            return table[self.box_char]
        raise KeyError(f"The first character of `{self.text}` is not one of (+, -)")

    def __repr__(self):
        return f"{self.box_char}{self.color} {self.display_text}"


def read_file(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            return ""
    with open(filename) as f:
        return f.read()


def validate_file(data):
    if len(data) == 0:
        return []
    lines = data.split("\n")
    for i in lines.copy():
        if len(i) == 0:
            lines.remove(i)
            continue
    return lines


def get_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Todo list",
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Controls:\n  " + "\n  ".join(md_table_to_lines(HELP_FILE, 29, 41)),
    )
    parser.add_argument(
        "--help",
        action="help",
        help="Show this help message and exit.",
    )
    parser.add_argument(
        "--autosave",
        "-s",
        action="store_true",
        default=AUTOSAVE,
        help="Boolean: determines if file is saved on every\
            action or only once at the program termination.",
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
        "-t",
        action="store_true",
        default=STRIKETHROUGH,
        help="Boolean: strikethrough completed todos\
            - option to disable because some terminals\
            don't support strikethroughs.",
    )
    parser.add_argument(
        "--header",
        "-h",
        type=str,
        default=HEADER,
        help=f"Allows passing alternate header. Default is `{HEADER}`.",
    )
    parser.add_argument(
        "--help-file",
        type=str,
        default=HELP_FILE,
        help=f"Allows passing alternate file to specify help menu. Default is `{HELP_FILE}`.",
    )
    return parser.parse_args()


def handle_args(args):
    global AUTOSAVE, FILENAME, HELP_FILE, STRIKETHROUGH, HEADER
    AUTOSAVE = args.autosave
    FILENAME = args.filename
    HELP_FILE = args.help_file
    STRIKETHROUGH = args.strikethrough
    HEADER = args.header


def ensure_within_bounds(counter, minimum, maximum):
    if counter < minimum:
        return minimum
    elif counter > maximum - 1:
        return maximum - 1
    else:
        return counter


def toggle_completed(char):
    if char == "+":
        return "-"
    elif char == "-":
        return "+"


def update_file(filename, lst, save=AUTOSAVE):
    if not save:
        return 0
    with open(filename, "w") as f:
        return f.write("\n".join([repr(i) for i in lst]))


def wgetnstr(win, n=1024, chars="", cursor="█"):
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
            Initial string to occupy the window. Defaults to "" (empty string).
        cursor (str, optional):
            Cursor character to display while typing. Defaults to "█".

    Returns:
        str: Similar to the built in input() function, returns a string of what the user entered.
    """
    assert (
        win.getmaxyx()[0] >= 3
    ), "Window is too short, it won't be able to display the minimum 1 line of text."
    original = chars
    win.box()
    win.nodelay(False)
    win.addstr(1, 1, f"{chars}{cursor}")
    while True:
        try:
            ch = win.getch()
        except KeyboardInterrupt:  # ctrl+c
            return original
        if ch in (10, 13):  # enter
            break
        elif ch == 127:  # backspace
            chars = chars[:-1]
            win.addstr(1, len(chars) + 1, f"{cursor} ")
        elif ch == 27:  # escape
            return original
        elif ch == 260:  # left arrow
            pass
        elif ch == 261:  # right arrow
            pass
        else:
            if len(chars) < n:
                ch = chr(ch)
                chars += ch
                win.addstr(1, len(chars), f"{ch}{cursor}")
            else:
                curses.beep()
        win.refresh()

    return chars


def hline(win, y, x, ch, n):
    win.addch(y, x, curses.ACS_LTEE)
    win.hline(y, x + 1, ch, n - 2)
    win.addch(y, x + n - 1, curses.ACS_RTEE)


def insert_todo(stdscr, todos: list, index, existing_todo=False):
    y, x = stdscr.getmaxyx()
    input_win = curses.newwin(3, x // 2, y // 2 - 3, x // 4)
    if existing_todo:
        todos[index] = Todo(
            f"- {wgetnstr(input_win, chars=todos[index].split(' ', 1)[1])}"
        )
    else:
        if (todo := wgetnstr(input_win)) == "":
            return todos
        todos.insert(index, Todo(f"- {todo}"))
    return todos


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


def maxlen(iterable):
    return len(max(iterable, key=len))


def md_table_to_lines(filename, first_line_idx, last_line_idx):
    with open(filename) as f:
        lines = f.readlines()[first_line_idx - 1 : last_line_idx - 1]
    for i, _ in enumerate(lines):
        lines[i] = lines[i].replace("<kbd>", "").replace("</kbd>", "").split("|")[1:-1]
    lines[1] = ("-", "-")
    key_max = maxlen([k.strip() for k, _ in lines])
    value_max = maxlen(v.strip() for _, v in lines)
    lines[1] = ("-" * (key_max + 2), "-" * value_max)
    for i, (k, v) in enumerate(lines):
        lines[i] = (k.strip() + " " * (key_max - len(k.strip()) + 2) + v.strip()).ljust(
            key_max + value_max + 2
        )
    return lines


def help_menu(parent_win):
    parent_win.clear()
    parent_win.addstr(0, 0, "Help:", curses.A_BOLD)
    lines = md_table_to_lines(HELP_FILE, 29, 41)
    win = curses.newwin(
        len(lines) + 2,
        len(lines[0]) + 2,
        1,
        (parent_win.getmaxyx()[1] - (len(lines[0]) + 1)) // 2,
    )
    win.box()
    for i, v in enumerate(lines):
        win.addstr(i + 1, 1, v)
    hline(win, 2, 0, curses.ACS_HLINE, win.getmaxyx()[1])
    parent_win.refresh()
    win.refresh()
    return win.getch()


def get_color(color):
    return COLORS[color]


def color_menu(parent_win):
    parent_win.clear()
    parent_win.addstr(0, 0, "Colors:", curses.A_BOLD)
    lines = [
        "Red    ",
        "Green  ",
        "Yellow ",
        "Blue   ",
        "Magenta",
        "Cyan   ",
        "White  ",
    ]
    win = curses.newwin(
        len(lines) + 2,
        len(lines[0]) + 2,
        1,
        (parent_win.getmaxyx()[1] - (len(lines[0]) + 1)) // 2,
    )
    win.box()
    selected = 0
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
            return get_color(lines[selected].strip())
        if key == 107:  # k
            selected -= 1
        elif key == 106:  # j
            selected += 1
        elif key == 103:  # g
            selected = 0
        elif key == 71:  # G
            selected = len(lines)
        elif key in (113, 27):  # q | esc
            return
        elif key == 10:  # enter
            return get_color(lines[selected].strip())
        elif key in range(49, 56):  # numbers
            selected = key - 49
        else:
            continue
        selected = ensure_within_bounds(selected, 0, len(lines))
        parent_win.refresh()
        win.refresh()


def print_todos(win, todos, selected):
    for i, v in enumerate(todos):
        win.addstr(
            i + 1,
            0,
            f"{v.get_box()}  ",
            curses.color_pair(v.color or get_color("White"))
            | (curses.A_REVERSE if i == selected else 0),
        )
        win.addstr(
            i + 1,
            3,
            strikethrough(v.display_text) if v.startswith("+") else v.display_text,
            curses.color_pair(v.color or get_color("White"))
            | (curses.A_REVERSE if i == selected else 0),
        )


def main(stdscr, header):
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

    todo = [Todo(i) for i in validate_file(read_file(FILENAME))]
    selected = 0
    # revert_with = None

    while True:
        stdscr.addstr(0, 0, f"{header}:")
        print_todos(stdscr, todo, selected)
        try:
            key = stdscr.getch()  # python3 -c "print(ord('x'))"
        except KeyboardInterrupt:  # exit on ^C
            return update_file(FILENAME, todo, True)
        if key in (259, 107):  # up | k
            selected -= 1
            # revert_with = ACTIONS["MOVEDOWN"]
        elif key in (258, 106):  # down | j
            selected += 1
            # revert_with = ACTIONS["MOVEUP"]
        elif key == 75:  # K
            todo = swap_todos(todo, selected, selected - 1)
            stdscr.clear()
            selected -= 1
            update_file(FILENAME, todo)
        elif key == 74:  # J
            todo = swap_todos(todo, selected, selected + 1)
            stdscr.clear()
            selected += 1
            update_file(FILENAME, todo)
        elif key == 111:  # o
            temp = todo.copy()
            todo = insert_todo(stdscr, todo, selected + 1)
            stdscr.clear()
            if temp != todo:
                selected += 1
            update_file(FILENAME, todo)
            # revert_with = ACTIONS["REMOVE"]
        elif key == 79:  # O
            temp = todo.copy()
            todo = insert_todo(stdscr, todo, selected)
            stdscr.clear()
            update_file(FILENAME, todo)
            # revert_with = ACTIONS["REMOVE"]
        elif key == 100:  # d
            todo = remove_todo(todo, selected)
            stdscr.clear()
            selected -= 1
            update_file(FILENAME, todo)
            # revert_with = ACTIONS["INSERT"]
        elif key == 117:  # u
            pass  # undo remove (or last action)
        elif key == 99:  # c
            todo[selected].set_color(color_menu(stdscr))
            stdscr.clear()
            update_file(FILENAME, todo)
        elif key == 105:  # i
            todo = insert_todo(stdscr, todo, selected, True)
            stdscr.clear()
            update_file(FILENAME, todo)
            # revert_with = ACTIONS["EDIT"]
        elif key == 103:  # g
            selected = 0
        elif key == 71:  # G
            selected = len(todo)
        elif key == 104:  # h
            help_menu(stdscr)
            stdscr.clear()
        elif key in (113, 27):  # q | esc
            return update_file(FILENAME, todo, True)
        elif key == 10:  # enter
            todo[selected] = Todo(
                toggle_completed(todo[selected][0]) + todo[selected][1:],
                color=todo[selected].color,
            )
            update_file(FILENAME, todo)
            # revert_with = ACTIONS["TOGGLE"]
        else:
            continue
        selected = ensure_within_bounds(selected, 0, len(todo))
        stdscr.refresh()


if __name__ == "__main__":
    handle_args(get_args())
    curses.wrapper(main, header=HEADER)
