
import py, os
from pypy.translator.platform import Platform, CompilationError, ExecutionResult
from pypy.translator.platform import log, _run_subprocess
from pypy.tool import autopath
from pypy.translator.platform.posix import GnuMakefile, BasePosix

class Linux(BasePosix):
    name = "linux"
    
    link_flags = ['-pthread']
    cflags = ['-O3', '-pthread', '-fomit-frame-pointer']
    standalone_only = []
    shared_only = []
    so_ext = 'so'
    
    def _args_for_shared(self, args):
        return ['-shared'] + args

    def _compile_o_files(self, cfiles, eci, standalone=True):
        cfiles = [py.path.local(f) for f in cfiles]
        cfiles += [py.path.local(f) for f in eci.separate_module_files]
        compile_args = self._compile_args_from_eci(eci, standalone)
        ofiles = []
        for cfile in cfiles:
            ofiles.append(self._compile_c_file(self.cc, cfile, compile_args))
        return ofiles
        
    def gen_makefile(self, cfiles, eci, exe_name=None, path=None):
        cfiles = [py.path.local(f) for f in cfiles]
        cfiles += [py.path.local(f) for f in eci.separate_module_files]

        if path is None:
            path = cfiles[0].dirpath()

        pypypath = py.path.local(autopath.pypydir)

        if exe_name is None:
            exe_name = cfiles[0].new(ext=self.exe_ext)

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

        rel_includedirs = [pypyrel(incldir) for incldir in
                           self._preprocess_dirs(eci.include_dirs)]

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
        self._handle_error(returncode, stdout, stderr, path.join('make'))

    def include_dirs_for_libffi(self):
        return ['/usr/include/libffi']

    def library_dirs_for_libffi(self):
        return ['/usr/lib/libffi']


class Linux64(Linux):
    shared_only = ['-fPIC']
