"""
Printing Utilities, Based on https://github.com/bchao1/bullet
"""
import enum
import shutil
import sys


TERMINAL_WIDTH, _ = shutil.get_terminal_size()

CURSOR_TO_CHAR = {"UP": "A", "DOWN": "B", "RIGHT": "C", "LEFT": "D"}

COLORS = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "default": 39,
}


class Direction(enum.Enum):
    UP = 0
    DOWN = 1


def forceWrite(content, end=""):
    sys.stdout.write(str(content) + end)
    sys.stdout.flush()


def writeColor(content, color, end=""):
    forceWrite(f"\u001b[{COLORS[color]}m{content}\u001b[0m", end)


def reset_cursor():
    forceWrite("\r")


def move_cursor(num_lines: int, direction: str):
    forceWrite(f"\033[{num_lines}{CURSOR_TO_CHAR[direction.upper()]}")


def clear_line():
    forceWrite(" " * TERMINAL_WIDTH)
    reset_cursor()


def linebreak():
    reset_cursor()
    forceWrite("-" * TERMINAL_WIDTH)
