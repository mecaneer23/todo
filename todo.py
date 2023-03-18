#!/usr/bin/env python3

import curses
import os

FILENAME = "todo.txt"


def read_file(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            return ""
    with open(filename) as f:
        return f.read()


def validate_file(data):
    if len(data) == 0:
        return
    lines = data.split("\n")
    for i in lines.copy():
        if len(i) == 0:
            lines.remove(i)
            continue
        assert i[0] in "+-", f"not a vaild file: line {i}"
    return lines


def ensure_within_bounds(counter, minimum, maximum):
    if counter < minimum:
        return minimum
    elif counter > maximum - 1:
        return maximum - 1
    else:
        return counter


def format_item(item):
    table = {
        "+": "x",
        "-": " ",
    }
    return f"- [{table[item[0]]}] {item.split(' ', 1)[1]}"


def toggle_completed(char):
    if char == "+":
        return "-"
    elif char == "-":
        return "+"


def update_file(filename, lst):
    with open(filename, "w") as f:
        return f.write("\n".join(lst))


def main(stdscr):
    curses.use_default_colors()
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(2, -1, -1)

    todo = validate_file(read_file(FILENAME))
    selected = 0
    while True:
        stdscr.addstr(0, 0, "TODO:")
        for i, v in enumerate(todo):
            stdscr.addstr(i + 1, 0, format_item(v), curses.color_pair(1 if i == selected else 2))
        try:
            key = stdscr.getch()
        except KeyboardInterrupt:  # exit on ^C
            return
        if key in (119, 259, 107):  # w | ^ | k
            selected -= 1
        elif key in (115, 258, 106):  # s | v | j
            selected += 1
        elif key in (113, 27):  # q | esc
            return
        elif key == 10:  # enter
            todo[selected] = toggle_completed(todo[selected][0]) + todo[selected][1:]
            update_file(FILENAME, todo)
        else:
            continue
        selected = ensure_within_bounds(selected, 0, len(todo))
        stdscr.refresh()


if __name__ == "__main__":
    curses.wrapper(main)
