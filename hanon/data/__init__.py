import sys
import os


def open_data(name, mode='r'):
    if getattr(sys, 'frozen', False):
        path = os.path.join(sys._MEIPASS, 'data', name)
    else:
        path = os.path.join(os.path.dirname(__file__), name)
    return open(path, mode)
