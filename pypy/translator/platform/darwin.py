
import py, os
from pypy.translator.platform import linux # xxx

class Darwin(linux.Linux): # xxx
    link_extra = []
    cflags = ['-O3', '-fomit-frame-pointer']
    
    def __init__(self, cc='gcc'):
        self.cc = cc

    def _args_for_shared(self, args):
        return ['-bundle', '-undefined', 'dynamic_lookup'] + args
