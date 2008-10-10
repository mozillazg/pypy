
import py
from pypy.translator.platform import Platform, CompilationError, ExecutionResult
from subprocess import PIPE, Popen

def _run_subprocess(args):
    pipe = Popen(args, executable=args[0],
                 stdout=PIPE, stderr=PIPE, shell=False)
    stdout, stderr = pipe.communicate()
    return pipe.returncode, stdout, stderr

class Linux(Platform):
    def __init__(self, cc='gcc'):
        self.cc = cc

    def compile(self, cfiles, eci):
        cfiles = [py.path.local(f) for f in cfiles]
        # XXX ignore eci
        args = [self.cc] + [str(f) for f in cfiles]
        exe_name = cfiles[0].dirpath().join(cfiles[0].purebasename)
        args += ['-o', str(exe_name)]
        returncode, stdout, stderr = _run_subprocess(args)
        if returncode != 0:
            raise CompilationError(stdout, stderr)
        return exe_name

    def execute(self, executable):
        returncode, stdout, stderr = _run_subprocess([str(executable)])
        return ExecutionResult(returncode, stdout, stderr)
