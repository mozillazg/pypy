
import py, os
from pypy.translator.platform import Platform, CompilationError, ExecutionResult
from pypy.translator.platform import log
from subprocess import PIPE, Popen
from pypy.tool import autopath

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

class Definition(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def write(self, f):
        def write_list(prefix, lst):
            for i, fn in enumerate(lst):
                print >> f, prefix, fn,
                if i < len(lst)-1:
                    print >> f, '\\'
                else:
                    print >> f
                prefix = ' ' * len(prefix)
        name, value = self.name, self.value
        if isinstance(value, str):
            f.write('%s = %s\n' % (name, value))
        else:
            write_list('%s =' % (name,), value)
        
class Rule(object):
    def __init__(self, target, deps, body):
        self.target = target
        self.deps   = deps
        self.body   = body

    def write(self, f):
        target, deps, body = self.target, self.deps, self.body
        dep_s = ' '.join(deps)
        f.write('%s: %s\n' % (target, dep_s))
        if isinstance(body, str):
            f.write('\t%s\n' % body)
        else:
            f.write('\t%s\n' % '\n\t'.join(body))
        f.write('\n')

class Comment(object):
    def __init__(self, body):
        self.body = body

    def write(self, f):
        f.write('# %s\n' % (self.body,))

class GnuMakefile(object):
    def __init__(self):
        self.lines = []

    def definition(self, name, value):
        self.lines.append(Definition(name, value))

    def rule(self, target, deps, body):
        self.lines.append(Rule(target, deps, body))

    def comment(self, body):
        self.lines.append(Comment(body))

    def write(self, f):
        for line in self.lines:
            line.write(f)
        f.flush()

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

    def gen_makefile(self, cfiles, eci, exe_name=None, path=None):
        m = GnuMakefile()
        # XXX cfiles relative to path
        m.comment('automatically generated makefile')
        definitions = [
            ('PYPYDIR', str(autopath.pypy_dir)),
            ('TARGET', exe_name.basename),
            ('DEFAULT_TARGET', '$(TARGET)'),
            ('SOURCES', whacked_cfiles),
            ('OBJECTS', whacked_ofiles),
            ('LIBS', whacked_libs),
            ]
        for args in definitions:
            m.definition(*args)
        # <hack>
        #for includedir in eci.include_dirs:
        #    if includedir.relto
        # </hack>
