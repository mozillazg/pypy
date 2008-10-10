
import py, os
from pypy.translator.platform import Platform, CompilationError, ExecutionResult
from subprocess import PIPE, Popen

from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("cbuild")
py.log.setconsumer("cbuild", ansi_log)

def _run_subprocess(args):
    pipe = Popen(args, executable=args[0],
                 stdout=PIPE, stderr=PIPE, shell=False)
    stdout, stderr = pipe.communicate()
    return pipe.returncode, stdout, stderr

class Linux(Platform):
    def __init__(self, cc='gcc'):
        self.cc = cc

    def _args_from_eci(self, cfiles, eci):
        include_dirs = ['-I%s' % (idir,) for idir in eci.include_dirs]
        library_dirs = ['-L%s' % (ldir,) for ldir in eci.library_dirs]
        libraries = ['-l%s' % (lib,) for lib in eci.libraries]
        return (include_dirs + [str(f) for f in cfiles] +
                library_dirs + libraries)

    def _args_for_shared(self, args):
        return ['-shared'] + args

    def compile(self, cfiles, eci, outputfilename=None, standalone=True):
        cfiles = [py.path.local(f) for f in cfiles]
        cfiles += [py.path.local(f) for f in eci.separate_module_files]
        args = self._args_from_eci(cfiles, eci)
        if outputfilename is None:
            outputfilename = cfiles[0].purebasename
        exe_name = py.path.local(os.path.join(str(cfiles[0].dirpath()),
                                              outputfilename))
        if not standalone:
            exe_name += '.so'
        args += ['-o', str(exe_name)]
        if not standalone:
            args = self._args_for_shared(args)
        args = [self.cc] + args
        log.execute(' '.join(args))
        returncode, stdout, stderr = _run_subprocess(args)
        if returncode != 0:
            errorfile = exe_name.new(ext='errors')
            errorfile.write(stderr)
            stderrlines = stderr.splitlines()
            for line in stderrlines[:5]:
                log.ERROR(line)
            if len(stderrlines) > 5:
                log.ERROR('...')
            raise CompilationError(stdout, stderr)
        return exe_name

    def execute(self, executable):
        returncode, stdout, stderr = _run_subprocess([str(executable)])
        return ExecutionResult(returncode, stdout, stderr)
