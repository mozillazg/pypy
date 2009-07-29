import autopath
import py
import os
import glob

from pypy.lang.io.model import W_Number, parse_literal, W_Message
from pypy.lang.io.objspace import ObjSpace

io_file = py.magic.autopath().dirpath().join("parserhack.io")

def parse(input, space=None):
    child_in, child_out_err = os.popen4("osxvm %s" % io_file)
    child_in.write(input)
    child_in.close()
    s = child_out_err.read().strip()
    print s
    return eval(s)

def interpret(code):
    space = ObjSpace()
    load_io_files(space)
    ast = parse(code, space)
    return ast.eval(space, space.w_lobby, space.w_lobby), space
    
def parse_file(filename, space=None):
    f = file(filename)
    code = f.read()
    f.close()
    return parse(code, space)
    
def load_io_files(space):
    files = glob.glob('io/*.io')
    for f in files:
        parse_file(f, space).eval(space, space.w_lobby, space.w_lobby)
    
    
if __name__ == '__main__':
    import sys
    space = ObjSpace()
    parse(py.path.local(sys.argv[1]).read(), space)