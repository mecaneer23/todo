# pylint: disable=missing-class-docstring, import-error
# pylint: disable=missing-function-docstring, missing-module-docstring

from src.class_todo import Todo


class Restorable:
    def __init__(self, todos: list[Todo], selected: int) -> None:
        self.stored: str = " |SEP|".join([todo.text for todo in todos])
        self.selected: int = selected

    def get(self) -> tuple[list[Todo], int]:
        stored = self.stored.split(" |SEP|")
        return [Todo(line) for line in stored], self.selected

    def __repr__(self) -> str:
        return self.stored.replace(" |SEP|", ", ") + f": {self.selected}"


class UndoRedo:
    def __init__(self) -> None:
        self.history: list[Restorable] = []
        self.index: int = -1

    def add(self, todos: list[Todo], selected: int) -> None:
        self.history.append(Restorable(todos, selected))
        self.index = len(self.history) - 1

    def undo(self) -> tuple[list[Todo], int]:
        if self.index > 0:
            self.index -= 1
        return self.history[self.index].get()

    def redo(self) -> tuple[list[Todo], int]:
        if self.index < len(self.history) - 1:
            self.index += 1
        return self.history[self.index].get()

    def __repr__(self) -> str:
        return (
            "\n".join(
                f"{'>' if i == self.index else ' '}  {v}"
                for i, v in enumerate(self.history)
            )
            + f"\nlength: ({len(self.history)})\nindex: ({self.index})"
        )
