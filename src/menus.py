"""
Various helpful menus and their helper functions.
"""

from itertools import tee
from typing import Callable, Iterable

try:
    from pyfiglet import figlet_format as big

    FIGLET_FORMAT_EXISTS = True
except ImportError:
    FIGLET_FORMAT_EXISTS = False  # pyright: ignore[reportConstantRedefinition]

from src.class_cursor import Cursor
from src.class_todo import Todo, TodoList, Todos
from src.get_args import (
    CONTROLS_BEGIN_INDEX,
    CONTROLS_END_INDEX,
    FILENAME,
    HELP_FILE,
    TKINTER_GUI,
)
from src.get_todo import get_todo, hline
from src.io import update_file
from src.keys import Key
from src.md_to_py import md_table_to_lines
from src.print_todos import make_printable_sublist
from src.utils import Color, clamp, overflow, set_header

if TKINTER_GUI:
    import src.tcurses as curses
else:
    import curses  # type: ignore


def _simple_scroll_keybinds(
    win: curses.window, cursor: int, len_lines: int, len_new_lines: int
) -> int:
    try:
        key = win.getch()
    except Key.ctrl_c:
        return -1
    if key in (Key.up, Key.k):
        cursor = clamp(cursor - 1, 0, len_lines - 2)
    elif key in (Key.down, Key.j, Key.enter):
        cursor = clamp(cursor + 1, 0, len_lines - len_new_lines - 1)
    else:
        return -1
    return cursor


def _get_move_options(
    len_list: int, additional_options: dict[int, Callable[[int], int]]
) -> dict[int, Callable[[int], int]]:
    defaults: dict[int, Callable[[int], int]] = {
        Key.k: lambda cursor: cursor - 1,
        Key.j: lambda cursor: cursor + 1,
        Key.g: lambda _: 0,
        Key.G: lambda _: len_list - 1,
    }
    return defaults | additional_options


def help_menu(parent_win: curses.window) -> None:
    """Show a scrollable help menu, generated from the README"""
    parent_win.clear()
    set_header(parent_win, "Help (k/j to scroll):")
    lines: list[str] = []
    for line in md_table_to_lines(
        CONTROLS_BEGIN_INDEX,
        CONTROLS_END_INDEX,
        str(HELP_FILE),
        frozenset({"<kbd>", "</kbd>", "(arranged alphabetically)"}),
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
        new_lines, _, _ = make_printable_sublist(
            win.getmaxyx()[0] - 4, lines[2:], cursor, 0
        )
        for i, line in enumerate(new_lines):
            win.addstr(i + 3, 1, line)
        win.refresh()
        cursor = _simple_scroll_keybinds(win, cursor, len(lines), len(new_lines))
        if cursor < 0:
            break
    parent_win.clear()


def magnify_menu(stdscr: curses.window, todos: Todos, selected: Cursor) -> None:
    """
    Magnify the first line of the current selection using pyfiglet.

    The magnified content is scrollable if it should be.
    """
    if not FIGLET_FORMAT_EXISTS:
        set_header(stdscr, "Magnify dependency not available")
        return
    stdscr.clear()
    set_header(stdscr, "Magnifying...")
    lines = big(  # pyright: ignore
        todos[int(selected)].get_display_text(), width=stdscr.getmaxyx()[1]
    ).split("\n")
    lines.append("")
    lines = [line.ljust(stdscr.getmaxyx()[1] - 2) for line in lines]
    cursor = 0
    while True:
        new_lines, _, _ = make_printable_sublist(
            stdscr.getmaxyx()[0] - 2, lines, cursor, 0
        )
        for i, line in enumerate(new_lines):
            stdscr.addstr(i + 1, 1, line)
        stdscr.refresh()
        cursor = _simple_scroll_keybinds(stdscr, cursor, len(lines), len(new_lines))
        if cursor < 0:
            break
    stdscr.refresh()
    stdscr.clear()


def color_menu(parent_win: curses.window, original: Color) -> Color:
    """Show a menu to choose a color. Return the chosen Color."""
    parent_win.clear()
    set_header(parent_win, "Colors:")
    lines = [i.ljust(len(max(Color.as_dict(), key=len))) for i in Color.as_dict()]
    win = curses.newwin(
        len(lines) + 2,
        len(lines[0]) + 2,
        1,
        (parent_win.getmaxyx()[1] - (len(lines[0]) + 1)) // 2,
    )
    win.box()
    move_options = _get_move_options(
        len(lines),
        {
            Key.one: lambda _: 0,
            Key.two: lambda _: 1,
            Key.three: lambda _: 2,
            Key.four: lambda _: 3,
            Key.five: lambda _: 4,
            Key.six: lambda _: 5,
            Key.seven: lambda _: 6,
        },
    )
    cursor = original.as_int() - 1
    while True:
        parent_win.refresh()
        for i, line in enumerate(lines):
            win.addstr(
                i + 1,
                1,
                line,
                curses.color_pair(Color.as_dict()[line.strip()])
                | (curses.A_STANDOUT if i == cursor else 0),
            )
        try:
            key = win.getch()
        except KeyboardInterrupt:
            return original
        return_options: dict[int, Callable[[], Color]] = {
            Key.q: lambda: original,
            Key.escape: lambda: original,
            Key.enter: lambda: Color(Color.as_dict()[lines[cursor].strip()]),
        }
        if key in move_options:
            move_func = move_options[key]
            cursor = move_func(cursor)
        elif key in return_options:
            return return_options[key]()
        else:
            continue
        cursor = overflow(cursor, 0, len(lines))
        parent_win.refresh()
        win.refresh()


def _get_sorting_methods() -> dict[str, Callable[[Todos], str]]:
    return {
        "Alphabetical": lambda top_level_todo: top_level_todo[0].get_display_text(),
        "Completed": lambda top_level_todo: (
            "1" if top_level_todo[0].is_toggled() else "0"
        ),
        "Color": lambda top_level_todo: str(top_level_todo[0].get_color()),
    }


def _get_indented_sections(todos: Todos) -> list[Todos]:
    indented_sections: list[Todos] = []
    section: Todos = Todos([])
    for todo in todos:
        if todo.get_indent_level() > 0:
            section.append(todo)
            continue
        if len(section) > 0:
            indented_sections.append(section)
        section = Todos([todo])
    indented_sections.append(section)
    return indented_sections


def _sort_by(method: str, todos: Todos, selected: Cursor) -> TodoList:
    key = _get_sorting_methods()[method]
    selected_todo = todos[int(selected)]
    sorted_todos = Todos([])
    for section in sorted(_get_indented_sections(todos), key=key):
        for todo in section:
            sorted_todos.append(todo)
    update_file(FILENAME, sorted_todos)
    return TodoList(sorted_todos, sorted_todos.index(selected_todo))


def sort_menu(parent_win: curses.window, todos: Todos, selected: Cursor) -> TodoList:
    """
    Show a menu to choose a method to sort the `Todos`.
    Immediately sort the list and return the sorted list.
    """
    parent_win.clear()
    set_header(parent_win, "Sort by:")
    lines = list(_get_sorting_methods().keys())
    win = curses.newwin(
        len(lines) + 2,
        len(lines[0]) + 2,
        1,
        (parent_win.getmaxyx()[1] - (len(max(lines, key=len)) + 1)) // 2,
    )
    win.box()
    move_options = _get_move_options(len(lines), {})
    cursor = 0
    while True:
        parent_win.refresh()
        for i, line in enumerate(lines):
            win.addstr(
                i + 1,
                1,
                line,
                curses.A_STANDOUT if i == cursor else 0,
            )
        try:
            key = win.getch()
        except KeyboardInterrupt:
            return TodoList(todos, int(selected))
        return_options: dict[int, Callable[..., TodoList]] = {
            Key.q: lambda: TodoList(todos, int(selected)),
            Key.escape: lambda: TodoList(todos, int(selected)),
            Key.enter: lambda: _sort_by(lines[cursor], todos, selected),
        }
        if key in move_options:
            func = move_options[key]
            cursor = func(cursor)
        elif key in return_options:
            return return_options[key]()
        else:
            continue
        cursor = clamp(cursor, 0, len(lines))
        parent_win.refresh()
        win.refresh()


def get_newwin(stdscr: curses.window) -> curses.window:
    """
    Create a curses.newwin in the center of the
    screen based on the width and height of the
    window passed in.
    """
    max_y, max_x = stdscr.getmaxyx()
    return curses.newwin(3, max_x * 3 // 4, max_y // 2 - 3, max_x // 8)


def search_menu(stdscr: curses.window, todos: Todos, selected: Cursor) -> None:
    """
    Open a menu to search for a given string.
    Move the cursor to the first location of
    that string.
    """
    set_header(stdscr, "Searching...")
    stdscr.refresh()
    sequence = get_todo(
        stdscr,
        get_newwin(stdscr),
        Todo(),
        Todo(),
    ).get_display_text()
    stdscr.clear()
    for i, todo in enumerate(todos[int(selected) :], start=int(selected)):
        if sequence in todo.get_display_text():
            selected.set_to(i)
            return
    selected.set_to(0)


def _chunk_message(message: str, width: int) -> Iterable[str]:
    left = 0
    right = width + 1
    while True:
        right -= 1
        if right >= len(message):
            yield message[left:]
            break
        if message[right] == " ":
            yield message[left:right]
            left = right + 1
            right += width
            continue
        if right == left:
            yield message[left : left + width]
            continue


def alert_menu(stdscr: curses.window, message: str) -> int:
    """
    Show a box with a message, similar to a JavaScript alert.

    Press any key to close (pressed key is returned).
    """
    set_header(stdscr, "Alert!")
    stdscr.refresh()
    border_width = 2
    max_y, max_x = stdscr.getmaxyx()
    height_chunk, width_chunk, chunks = tee(
        _chunk_message(message, max_x * 3 // 4 - border_width), 3
    )
    width = len(max(width_chunk, key=len)) + border_width
    height = sum(1 for _ in height_chunk) + border_width
    win = curses.newwin(height, width, max_y // 2 - height, max_x // 8)
    win.box()
    for index, chunk in enumerate(chunks, start=1):
        win.addstr(index, border_width // 2, chunk)
    win.refresh()
    return stdscr.getch()
