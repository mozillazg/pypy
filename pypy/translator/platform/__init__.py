
""" Platform object that allows you to compile/execute C sources for given
platform.
"""

import sys, py, os

from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("platform")
py.log.setconsumer("platform", ansi_log)

from subprocess import PIPE, Popen

def _run_subprocess(executable, args, env=None):
    if isinstance(args, str):
        args = str(executable) + ' ' + args
        shell = True
    else:
        if args is None:
            args = [str(executable)]
        else:
            args = [str(executable)] + args
        shell = False
    pipe = Popen(args, stdout=PIPE, stderr=PIPE, shell=shell, env=env)
    stdout, stderr = pipe.communicate()
    return pipe.returncode, stdout, stderr

class CompilationError(Exception):
    def __init__(self, out, err):
        self.out = out
        self.err = err

    def __repr__(self):
        return "<CompilationError instance>"

class ExecutionResult(object):
    def __init__(self, returncode, out, err):
        self.returncode = returncode
        self.out = out
        self.err = err

    def __repr__(self):
        return "<ExecutionResult retcode=%d>" % (self.returncode,)

class Platform(object):
    name = "abstract platform"
    
    def __init__(self, cc):
        self.cc = cc
    
    def compile(self, cfiles, eci, outputfilename=None, standalone=True):
        raise NotImplementedError("Pure abstract baseclass")

    def execute(self, executable, args=None, env=None):
        returncode, stdout, stderr = _run_subprocess(str(executable), args,
                                                     env)
        return ExecutionResult(returncode, stdout, stderr)

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

    # below are some detailed informations for platforms

    def include_dirs_for_libffi(self):
        raise NotImplementedError("Needs to be overwritten")

    def library_dirs_for_libffi(self):
        raise NotImplementedError("Needs to be overwritten")        

    def check___thread(self):
        return True

    
if sys.platform == 'linux2':
    from pypy.translator.platform.linux import Linux
    host = Linux()
elif sys.platform == 'darwin':
    from pypy.translator.platform.darwin import Darwin
    host = Darwin()
elif os.name == 'nt':
    from pypy.translator.platform.windows import Windows
    host = Windows()
else:
    # pray
    from pypy.translator.platform.distutils_platform import DistutilsPlatform
    host = DistutilsPlatform()

platform = host

def set_platform(new_platform, cc):
    global platform
    log.msg("Setting platform to %r cc=%s" % (new_platform,cc))
    if new_platform == 'host':
        platform = host.__class__(cc)
    elif new_platform == 'maemo':
        from pypy.translator.platform.maemo import Maemo
        platform = Maemo(cc)
    elif new_platform == 'distutils':
        from pypy.translator.platform.distutils_platform import DistutilsPlatform
        platform = DistutilsPlatform()
    else:
        raise NotImplementedError("platform = %s" % (new_platform,))
        

