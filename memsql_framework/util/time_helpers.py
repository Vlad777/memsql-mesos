import math
import time


def current_time():
    """ Returns the current time as a float. """
    return time.time()

def unix_timestamp():
    """ Returns the current unix timestamp as int (seconds since epoch). """
    return int(math.floor(current_time()))
