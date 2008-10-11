
""" Platform object that allows you to compile/execute C sources for given
platform.
"""

import sys, py

from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("platform")
py.log.setconsumer("platform", ansi_log)

class CompilationError(Exception):
    def __init__(self, out, err):
        self.out = out
        self.err = err

class ExecutionResult(object):
    def __init__(self, returncode, out, err):
        self.returncode = returncode
        self.out = out
        self.err = err

    def __repr__(self):
        return "<ExecutionResult retcode=%d>" % (self.returncode,)

class Platform(object):
    def __init__(self, cc):
        self.cc = cc
    
    def compile(self, cfiles, eci, outputfilename=None, standalone=True):
        raise NotImplementedError("Pure abstract baseclass")

    def execute(self, file_to_exec, args=None, env=None):
        raise NotImplementedError("Pure abstract baseclass")

    def gen_makefile(self, cfiles, eci, exe_name=None, path=None):
        raise NotImplementedError("Pure abstract baseclass")

    def __repr__(self):
        return '<%s cc=%s>' % (self.__class__.__name__, self.cc)

    def __hash__(self):
        return hash(self.__class__.__name__)

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.__dict__ == other.__dict__)

    def check___thread(self):
        return True

    
if sys.platform == 'linux2':
    from pypy.translator.platform.linux import Linux
    host = Linux()
elif sys.platform == 'darwin':
    from pypy.translator.platform.darwin import Darwin
    host = Darwin()
else:
    xxx
    

platform = host

def set_platform(new_platform, cc):
    global platform
    log.msg("Setting platform to %r cc=%s" % (new_platform,cc))
    if new_platform == 'host':
        platform = host.__class__(cc)
    elif new_platform == 'maemo':
        from pypy.translator.platform.maemo import Maemo
        platform = Maemo(cc)
    else:
        raise NotImplementedError("platform = %s" % (new_platform,))
        

