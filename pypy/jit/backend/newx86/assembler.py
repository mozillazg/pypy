from pypy.jit.backend.newx86.rx86 import R


class Assembler386(object):

    def __init__(self, cpu):
        self.cpu = cpu
        self.locations = {}

    def compile_loop(self, inputargs, operations, looptoken):
        xxx


def is_reg(loc):
    return loc >= 0

def is_stack(loc):
    return loc < 0
