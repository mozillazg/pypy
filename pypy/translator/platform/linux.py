
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
        if value:
            f.write('\n')
        
class Rule(object):
    def __init__(self, target, deps, body):
        self.target = target
        self.deps   = deps
        self.body   = body

    def write(self, f):
        target, deps, body = self.target, self.deps, self.body
        if isinstance(deps, str):
            dep_s = deps
        else:
            dep_s = ' '.join(deps)
        f.write('%s: %s\n' % (target, dep_s))
        if isinstance(body, str):
            f.write('\t%s\n' % body)
        elif body:
            f.write('\t%s\n' % '\n\t'.join(body))
        f.write('\n')

class Comment(object):
    def __init__(self, body):
        self.body = body

    def write(self, f):
        f.write('# %s\n' % (self.body,))

class GnuMakefile(object):
    def __init__(self, path=None):
        self.defs = {}
        self.lines = []
        self.makefile_dir = py.path.local(path)
        
    def pathrel(self, fpath):
        if fpath.dirpath() == self.makefile_dir:
            return fpath.basename
        elif fpath.dirpath().dirpath() == self.makefile_dir.dirpath():
            return '../' + fpath.relto(self.makefile_dir.dirpath())
        else:
            return str(fpath)

    def definition(self, name, value):
        defs = self.defs
        defn = Definition(name, value)
        if name in defs:
            self.lines[defs[name]] = defn
        else:
            defs[name] = len(self.lines)
            self.lines.append(defn)

    def rule(self, target, deps, body):
        self.lines.append(Rule(target, deps, body))

    def comment(self, body):
        self.lines.append(Comment(body))

    def write(self, out=None):
        if out is None:
            f = self.makefile_dir.join('Makefile').open('w')
        else:
            f = out
        for line in self.lines:
            line.write(f)
        f.flush()
        if out is None:
            f.close()

class Linux(Platform):
    link_flags = ['-pthread']
    cflags = ['-O3', '-pthread', '-fomit-frame-pointer']
    
    def __init__(self, cc=None):
        if cc is None:
            cc = 'gcc'
        self.cc = cc

    def _libs(self, libraries):
        return ['-l%s' % (lib,) for lib in libraries]

    def _libdirs(self, library_dirs):
        return ['-L%s' % (ldir,) for ldir in library_dirs]

    def _includedirs(self, include_dirs):
        return ['-I%s' % (idir,) for idir in include_dirs]

    def _compile_args_from_eci(self, eci):
        include_dirs = self._includedirs(eci.include_dirs)
        return (self.cflags + list(eci.compile_extra) + include_dirs)

    def _link_args_from_eci(self, eci):
        library_dirs = self._libdirs(eci.library_dirs)
        libraries = self._libs(eci.libraries)
        return (library_dirs + libraries + self.link_flags +
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
        self._handle_error(returncode, stderr, stdout, outname)

    def _handle_error(self, returncode, stderr, stdout, outname):
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
        cfiles = [py.path.local(f) for f in cfiles]
        cfiles += [py.path.local(f) for f in eci.separate_module_files]

        if path is None:
            path = cfiles[0].dirpath()

        pypypath = py.path.local(autopath.pypydir)

        if exe_name is None:
            exe_name = cfiles[0].new(ext='')

        m = GnuMakefile(path)
        m.exe_name = exe_name
        m.eci = eci

        def pypyrel(fpath):
            rel = py.path.local(fpath).relto(pypypath)
            if rel:
                return os.path.join('$(PYPYDIR)', rel)
            else:
                return fpath

        rel_cfiles = [m.pathrel(cfile) for cfile in cfiles]
        rel_ofiles = [rel_cfile[:-2]+'.o' for rel_cfile in rel_cfiles]
        m.cfiles = rel_cfiles

        rel_includedirs = [pypyrel(incldir) for incldir in eci.include_dirs]

        m.comment('automatically generated makefile')
        definitions = [
            ('PYPYDIR', autopath.pypydir),
            ('TARGET', exe_name.basename),
            ('DEFAULT_TARGET', '$(TARGET)'),
            ('SOURCES', rel_cfiles),
            ('OBJECTS', rel_ofiles),
            ('LIBS', self._libs(eci.libraries)),
            ('LIBDIRS', self._libdirs(eci.library_dirs)),
            ('INCLUDEDIRS', self._includedirs(rel_includedirs)),
            ('CFLAGS', self.cflags + list(eci.compile_extra)),
            ('LDFLAGS', self.link_flags + list(eci.link_extra)),
            ('CC', self.cc)
            ]
        for args in definitions:
            m.definition(*args)

        rules = [
            ('all', '$(DEFAULT_TARGET)', []),
            ('$(TARGET)', '$(OBJECTS)', '$(CC) $(LDFLAGS) -o $@ $(OBJECTS) $(LIBDIRS) $(LIBS)'),
            ('%.o', '%.c', '$(CC) $(CFLAGS) -o $@ -c $< $(INCLUDEDIRS)'),
            ]

        for rule in rules:
            m.rule(*rule)

        return m

    def execute_makefile(self, path_to_makefile):
        if isinstance(path_to_makefile, GnuMakefile):
            path = path_to_makefile.makefile_dir
        else:
            path = path_to_makefile
        log.execute('make in %s' % (path,))
        returncode, stdout, stderr = _run_subprocess('make', ['-C', str(path)])
        if returncode != 0:
            errorfile = path.join('make.errors')
            errorfile.write(stderr)
            stderrlines = stderr.splitlines()
            for line in stderrlines[:5]:
                log.ERROR(line)
            if len(stderrlines) > 5:
                log.ERROR('...')
            raise CompilationError(stdout, stderr)
