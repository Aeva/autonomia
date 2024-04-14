

from math import *


def zero_pad(num, digits = 2):
    s = str(num)
    n = max(digits - len(s), 0)
    return ("0" * n) + s
