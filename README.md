# Ndo - an ncurses todo application

A curses implementation of a todo list helper. Most of the keybindings are similar to vim-bindings so vim users should feel relatively comfortable.

## Running

```bash
python3 todo.py [options] [filename]
```

## Flags

Positional arguments:
| Argument | Description                                                          |
| -------- | -------------------------------------------------------------------- |
| filename | Provide a filename to store the todo list in. Default is `todo.txt`. |

Options:
| Option                     | Description                                                                                                     |
| -------------------------- | --------------------------------------------------------------------------------------------------------------- |
| --help                     | Show this help message and exit.                                                                                |
| --autosave, -s             | Boolean: determines if file is saved on every action or only once at the program termination.                   |
| --strikethrough, -t        | Boolean: strikethrough completed todos - option to disable because some terminals don't support strikethroughs. |
| --header HEADER, -h HEADER | Allows passing alternate header. Default is `TODO`.                                                             |
| --help-file HELP_FILE      | Allows passing alternate file to specify help menu. Default is `README.md`.                                     |

## Controls

| Keys                              | Description                 |
| --------------------------------- | --------------------------- |
| <kbd>h</kbd>                      | Show a list of controls     |
| <kbd>k</kbd>/<kbd>j</kbd>         | Move cursor up and down     |
| <kbd>K</kbd>/<kbd>J</kbd>         | Move todo up and down       |
| <kbd>o</kbd>                      | Add a new todo              |
| <kbd>O</kbd>                      | Add a todo on current line  |
| <kbd>d</kbd>                      | Remove selected todo        |
| <kbd>q</kbd>, <kbd>Ctrl + c</kbd> | Quit                        |
| <kbd>Enter</kbd>                  | Toggle a todo as completed  |
| <kbd>i</kbd>                      | Edit an existing todo       |
| <kbd>g</kbd>/<kbd>G</kbd>         | Jump to top/bottom of todos |
| <kbd>c</kbd>                      | Change selected todo color  |

## Bugs

- For some reason long todos don't render properly in strikethrough mode (in certain terminals)
