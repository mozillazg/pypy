
""" Platform object that allows you to compile/execute C sources for given
platform.
"""

import sys

class CompilationError(Exception):
    def __init__(self, out, err):
        self.out = out
        self.err = err

class ExecutionResult(object):
    def __init__(self, returncode, out, err):
        self.returncode = returncode
        self.out = out
        self.err = err

class Platform(object):
    def __init__(self, cc):
        self.cc = cc
    
    def compile(self, cfiles, eci, outputfilename=None, standalone=True):
        raise NotImplementedError("Pure abstract baseclass")

    def execute(self, file_to_exec):
        raise NotImplementedError("Pure abstract baseclass")

    def __repr__(self):
        return '<%s cc=%s>' % (self.__class__.__name__, self.cc)

if sys.platform == 'linux2':
    from pypy.translator.platform.linux import Linux
    host = Linux()
else:
    xxx
