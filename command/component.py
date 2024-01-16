"""
Main driver for the selection menu, based on https://github.com/bchao1/bullet
"""
from . import cursor, input
from .utils import (
    Direction,
    clear_line,
    forceWrite,
    linebreak,
    move_cursor,
    reset_cursor,
    writeColor,
)
from .keymap import KEYMAP


@input.register
class BulletMenu:
    """
    A CLI menu to select a choice from a list of choices using the keyboard.
    """

    def __init__(self, prompt: str = None, choices: dict[str, str] = None):
        self.position = 0
        self.prompt = prompt
        self.choices = list(choices.keys())
        self.descriptions = list(choices.values())
        self.arrow_char = ">>"

    def print_choice(self, index: int):
        "Prints the choice at the given index"
        if index == self.position:
            writeColor(f" {self.arrow_char} ", color="green")
            writeColor(
                f"{self.choices[index]:20}{self.descriptions[index]}", color="green"
            )
        else:
            forceWrite(f"    {self.choices[index]:20}{self.descriptions[index]}")
        reset_cursor()

    def move_direction(self, direction: Direction, num_spaces: int = 1):
        "Should not be directly called, used to move a direction of either up or down"
        old_position = self.position
        if direction == Direction.DOWN:
            if self.position + 1 >= len(self.choices):
                # go back to the top
                self.position = 0
                num_spaces = len(self.choices) - 1
                direction = Direction.UP
            else:
                self.position += num_spaces
        else:
            if self.position - 1 < 0:
                # go to the bottom
                self.position = len(self.choices) - 1
                num_spaces = len(self.choices) - 1
                direction = Direction.DOWN
            else:
                self.position -= num_spaces
        clear_line()
        self.print_choice(old_position)
        move_cursor(num_spaces, direction.name)
        self.print_choice(self.position)

    @input.mark(KEYMAP["up"])
    def move_up(self):
        self.move_direction(Direction.UP)

    @input.mark(KEYMAP["down"])
    def move_down(self):
        self.move_direction(Direction.DOWN)

    @input.mark(KEYMAP["newline"])
    def select(self):
        move_cursor(len(self.choices) - self.position, "DOWN")
        return self.position

    @input.mark(KEYMAP["interrupt"])
    def interrupt(self):
        move_cursor(len(self.choices) - self.position, "DOWN")
        raise KeyboardInterrupt

    @input.mark_multiple(*[KEYMAP[str(number)] for number in range(10)])
    def select_row(self):
        index = int(chr(self.current_selection))
        movement = index - self.position
        if index == self.position:
            return
        if index < len(self.choices):
            if self.position > index:
                self.move_direction(Direction.UP, -movement)
            elif self.position < index:
                self.move_direction(Direction.DOWN, movement)
            else:
                return
        else:
            return

    def run(self, default_choice: int = 0) -> str:
        "Start the menu and return the selected choice"
        if self.prompt:
            linebreak()
            forceWrite(self.prompt, "\n")
            writeColor(
                f"Tips: ↑↓选择，Enter确认",
                color="yellow",
                end="\n",
            )
        self.position = default_choice
        for i in range(len(self.choices)):
            self.print_choice(i)
            forceWrite("\n")
        move_cursor(len(self.choices) - self.position, "UP")
        with cursor.hide():
            while True:
                choice_index = self.handle_input()
                if choice_index is not None:
                    reset_cursor()
                    for _ in range(len(self.choices) + 2):
                        move_cursor(1, "UP")
                        clear_line()
                    forceWrite(f"{self.prompt}{self.choices[choice_index]}", "\n")
                    return self.choices[choice_index]
