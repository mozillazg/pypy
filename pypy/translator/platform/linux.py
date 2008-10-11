
import py, os
from pypy.translator.platform import Platform, CompilationError, ExecutionResult
from pypy.translator.platform import log
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

class Linux(Platform):
    link_extra = ['-pthread']
    cflags = ['-O3', '-pthread', '-fomit-frame-pointer']
    
    def __init__(self, cc='gcc'):
        self.cc = cc

    def _compile_args_from_eci(self, eci):
        include_dirs = ['-I%s' % (idir,) for idir in eci.include_dirs]
        return (self.cflags + list(eci.compile_extra) + include_dirs)

    def _link_args_from_eci(self, eci):
        library_dirs = ['-L%s' % (ldir,) for ldir in eci.library_dirs]
        libraries = ['-l%s' % (lib,) for lib in eci.libraries]
        return (library_dirs + libraries + self.link_extra +
                list(eci.link_extra))

    def _args_for_shared(self, args):
        return ['-shared'] + args

    def compile(self, cfiles, eci, outputfilename=None, standalone=True):
        cfiles = [py.path.local(f) for f in cfiles]
        cfiles += [py.path.local(f) for f in eci.separate_module_files]
        compile_args = self._compile_args_from_eci(eci)
        if outputfilename is None:
            outputfilename = cfiles[0].purebasename
        exe_name = py.path.local(os.path.join(str(cfiles[0].dirpath()),
                                              outputfilename))
        if not standalone:
            exe_name += '.so'
        ofiles = []
        for cfile in cfiles:
            ofiles.append(self._compile_c_file(self.cc, cfile, compile_args))
        return self._link(self.cc, ofiles, self._link_args_from_eci(eci),
                          standalone, exe_name)

    def _compile_c_file(self, cc, cfile, compile_args):
        oname = cfile.new(ext='o')
        args = ['-c'] + compile_args + [str(cfile), '-o', str(oname)]
        self._execute_c_compiler(cc, args, oname)
        return oname

    def _execute_c_compiler(self, cc, args, outname):
        log.execute(cc + ' ' + ' '.join(args))
        returncode, stdout, stderr = _run_subprocess(cc, args)
        if returncode != 0:
            errorfile = outname.new(ext='errors')
            errorfile.write(stderr)
            stderrlines = stderr.splitlines()
            for line in stderrlines[:5]:
                log.ERROR(line)
            if len(stderrlines) > 5:
                log.ERROR('...')
            raise CompilationError(stdout, stderr)
        
    def _link(self, cc, ofiles, link_args, standalone, exe_name):
        args = [str(ofile) for ofile in ofiles] + link_args
        args += ['-o', str(exe_name)]
        if not standalone:
            args = self._args_for_shared(args)
        self._execute_c_compiler(cc, args, exe_name)
        return exe_name

    def execute(self, executable, args=None, env=None):
        returncode, stdout, stderr = _run_subprocess(str(executable), args,
                                                     env)
        return ExecutionResult(returncode, stdout, stderr)
