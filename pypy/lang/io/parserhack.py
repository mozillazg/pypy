import py
import os
from pypy.lang.io.model import W_Number, parse_literal, W_Message
from pypy.lang.io.objspace import ObjSpace

io_file = py.magic.autopath().dirpath().join("parserhack.io")

def parse(input, space=None):
    child_in, child_out_err = os.popen4("osxvm %s" % io_file)
    child_in.write(input)
    child_in.close()
    s = child_out_err.read().strip()
    # print s
    return eval(s)

def interpret(code):
    space = ObjSpace()
    ast = parse(code, space)
    return ast.eval(space, space.w_lobby, space.w_lobby), space
    