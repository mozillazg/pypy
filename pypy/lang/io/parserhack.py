import autopath
import py
import os
import glob

from pypy.lang.io.model import W_Number, parse_literal, W_Message
from pypy.lang.io.objspace import ObjSpace

class MessageParser(object):
    def __init__(self, space, input,):
        self.space = space
        self.input = input
        self.position = 0
    def parse(self):
        while not self._char() == ')':
            self.next()
            name = self._read_name()

            arguments = self.parse_arguments()
            if self._char() == '(':
                nmsg = self.parse()
                self.next()
            else:
                nmsg = None
        return W_Message(self.space, name, arguments, nmsg)
    def _char(self):
        return self.input[self.position]
    def _prev_char(self):
        return self.input[self.position-1]
    def _next_char(self):
        return self.input[self.position+1]
    def _read_name(self):
        name = []
        assert self._char() == '"'
        self.next()
        while not self._char() == '"':
            if self._char() == '\\' and self._next_char() == '"':
                self.next()

            name.append(self._char())
            self.next()
        self.next()
        return ''.join(name)
        
    def next(self):
        self.position += 1
        
    def parse_arguments(self):
        arguments = []
        assert self._char() == '['
        self.next()
        while not self._char() == ']':
            arguments.append(self.parse())
            self.next()
            assert self._char() == ','
            self.next()
            
        assert self._char() == ']'
        self.next()
        return arguments
        
io_file = py.magic.autopath().dirpath().join("parserhack.io")

def parse(input, space=None):
    child_in, child_out_err = os.popen4("osxvm %s" % io_file)
    child_in.write(input)
    child_in.close()
    s = child_out_err.read().strip()
    # print s
    return MessageParser(space, s).parse()

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

    
def extract_name(input):
    re.match(input, '\"(\\"|[^"])+\"')
def load_io_files(space):
    files = glob.glob('io/*.io')
    for f in files:
        parse_file(f, space).eval(space, space.w_lobby, space.w_lobby)
    
    
if __name__ == '__main__':
    import sys
    space = ObjSpace()
    # print parse(py.path.local(sys.argv[1]).read(), space)
    print parse(sys.argv[1], space)
    
    
