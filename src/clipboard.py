"""
Clipboard functionality. If pyperclip is available, use it,
otherwise support copy/paste functionality only within Ndo.
"""

try:
    from pyperclip import copy, paste

    CLIPBOARD_EXISTS = True
except ImportError:
    CLIPBOARD_EXISTS = False  # pyright: ignore[reportConstantRedefinition]

from src.class_cursor import Cursor
from src.class_todo import Todo, Todos
from src.get_args import FILENAME, UI_TYPE, UiType
from src.io import update_file
from src.utils import alert

if UI_TYPE == UiType.ANSI:
    import src.acurses as curses
elif UI_TYPE == UiType.TKINTER:
    import src.tcurses as curses  # type: ignore
else:
    import curses  # type: ignore


def copy_todo(
    stdscr: curses.window,
    todos: Todos,
    selected: Cursor,
    copied_todo: Todo,
) -> None:
    """
    Set `copied_todo` to be a duplicate of the first selected Todo.
    If possible, also copy to the clipboard.
    """
    copied_todo.set_text(repr(todos[int(selected)]))
    if not CLIPBOARD_EXISTS:
        alert(
            stdscr,
            "Copied internally. External copy dependency not "
            "available: try running `pip install pyperclip`",
        )
        return
    copy(  # pyright: ignore[reportPossiblyUnboundVariable]
        "\n".join([todos[pos].get_display_text() for pos in selected.get()])
    )


def _todo_from_clipboard(
    stdscr: curses.window,
    todos: Todos,
    selected: int,
    copied_todo: Todo,
) -> Todos:
    """Retrieve copied_todo and insert into todo list"""
    if not CLIPBOARD_EXISTS:
        todos.insert(selected + 1, Todo(repr(copied_todo)))
        alert(
            stdscr,
            "Pasting from internal buffer. External paste dependency "
            "not available: try running `pip install pyperclip`",
        )
        return todos
    pasted = paste()  # pyright: ignore
    if copied_todo.get_display_text() == pasted:
        todos.insert(selected + 1, Todo(repr(copied_todo)))
        return todos
    for index, line in enumerate(pasted.strip().split("\n"), start=1):
        todos.insert(selected + index, Todo(f"- {line}"))
    return todos


def paste_todo(
    stdscr: curses.window,
    todos: Todos,
    selected: Cursor,
    copied_todo: Todo,
) -> Todos:
    """Paste a todo from copied_todo or clipboard if available"""
    temp = todos.copy()
    todos = _todo_from_clipboard(stdscr, todos, int(selected), copied_todo)
    stdscr.clear()
    if temp != todos:
        selected.single_down(len(todos))
    update_file(FILENAME, todos)
    return todos
