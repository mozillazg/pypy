# dummy implementations

import os

def begin():
    os.write(2, '= rtrans.begin\n')

def end():
    os.write(2, '= rtrans.end\n')

def retry():
    os.write(2, '= rtrans.retry\n')

def abort():
    os.write(2, '= rtrans.abort\n')

def pause():
    os.write(2, '= rtrans.pause\n')

def unpause():
    os.write(2, '= rtrans.unpause\n')

def verbose():
    os.write(2, '= rtrans.verbose\n')

def enable():
    os.write(2, '= rtrans.enable\n')

def disable():
    os.write(2, '= rtrans.disable\n')

def is_active():
    os.write(2, '= rtrans.is_active\n')
    return False

def reset_stats():
    os.write(2, '= rtrans.reset_stats\n')
