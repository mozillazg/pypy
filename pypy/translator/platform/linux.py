
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
    exe_ext = ''
    
    def _libs(self, libraries):
        return ['-l%s' % (lib,) for lib in libraries]

    def _libdirs(self, library_dirs):
        return ['-L%s' % (ldir,) for ldir in library_dirs]

    def _includedirs(self, include_dirs):
        return ['-I%s' % (idir,) for idir in include_dirs]

    def _compile_args_from_eci(self, eci, standalone):
        include_dirs = self._preprocess_dirs(eci.include_dirs)
        args = self._includedirs(include_dirs)
        if standalone:
            extra = self.standalone_only
        else:
            extra = self.shared_only
        cflags = self.cflags + extra
        return (cflags + list(eci.compile_extra) + args)

    def _link_args_from_eci(self, eci):
        library_dirs = self._libdirs(eci.library_dirs)
        libraries = self._libs(eci.libraries)
        return (library_dirs + libraries + self.link_flags +
                list(eci.link_extra))

    def _preprocess_dirs(self, include_dirs):
        # hook for maemo
        return include_dirs

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

    def compile(self, cfiles, eci, outputfilename=None, standalone=True):
        ofiles = self._compile_o_files(cfiles, eci, standalone)
        return self._finish_linking(ofiles, eci, outputfilename, standalone)

    def _finish_linking(self, ofiles, eci, outputfilename, standalone):
        if outputfilename is None:
            outputfilename = ofiles[0].purebasename
        exe_name = py.path.local(os.path.join(str(ofiles[0].dirpath()),
                                              outputfilename))
        if standalone:
            exe_name += '.' + self.exe_ext
        else:
            exe_name += '.' + self.so_ext
        return self._link(self.cc, ofiles, self._link_args_from_eci(eci),
                          standalone, exe_name)
        
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
