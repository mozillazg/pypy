
import py, os
from pypy.translator.platform import linux # xxx

class Darwin(linux.Linux): # xxx
    name = "darwin"
    
    link_flags = []
    cflags = ['-O3', '-fomit-frame-pointer']
    # -mdynamic-no-pic for standalone
    
    def __init__(self, cc='gcc'):
        self.cc = cc

    def _args_for_shared(self, args):
        return ['-bundle', '-undefined', 'dynamic_lookup'] + args

    def include_dirs_for_libffi(self):
        return ['/usr/include/ffi']

    def library_dirs_for_libffi(self):
        return []
