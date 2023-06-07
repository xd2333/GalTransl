"""
A utility for showing and hiding the terminal cursor on Windows and Linux, based on https://github.com/bchao1/bullet
"""
from contextlib import contextmanager
import ctypes


class _CursorInfo(ctypes.Structure):
    _fields_ = [("size", ctypes.c_int), ("visible", ctypes.c_byte)]


@contextmanager
def hide():
    try:
        _hide_cursor()
        yield
    finally:
        _show_cursor()


def _hide_cursor():
    ci = _CursorInfo()
    handle = ctypes.windll.kernel32.GetStdHandle(-11)
    ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
    ci.visible = False
    ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))


def _show_cursor():
    ci = _CursorInfo()
    handle = ctypes.windll.kernel32.GetStdHandle(-11)
    ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
    ci.visible = True
    ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))
