

from math import *


def zero_pad(num, digits = 2):
    s = str(num)
    n = max(digits - len(s), 0)
    return ("0" * n) + s


def lerp(x, y, a):
    return (1.0 - a) * x + y * a


def pretty_time(seconds):
    seconds = int(seconds)
    minutes = zero_pad(seconds // 60)
    seconds = zero_pad(seconds % 60)
    return f"{minutes}:{seconds}"
