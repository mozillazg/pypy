import autopath

import os, sys, inspect, re, imp
from pypy.translator.tool import stdoutcapture
from pypy.tool.autopath import pypydir
from pypy.translator.platform import host

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("cbuild")
py.log.setconsumer("cbuild", ansi_log)
from pypy.tool.udir import udir

debug = 0

CFLAGS = os.getenv("CFLAGS")
if CFLAGS:
    CFLAGS = CFLAGS.split()
else:
    CFLAGS = ['-O3']

class ExternalCompilationInfo(object):

    _ATTRIBUTES = ['pre_include_bits', 'includes', 'include_dirs',
                   'post_include_bits', 'libraries', 'library_dirs',
                   'separate_module_sources', 'separate_module_files',
                   'export_symbols', 'compile_extra', 'link_extra',
                   'frameworks']
    _DUPLICATES_OK = ['compile_extra', 'link_extra']

    def __init__(self,
                 pre_include_bits        = [],
                 includes                = [],
                 include_dirs            = [],
                 post_include_bits       = [],
                 libraries               = [],
                 library_dirs            = [],
                 separate_module_sources = [],
                 separate_module_files   = [],
                 export_symbols          = [],
                 compile_extra           = [],
                 link_extra              = [],
                 frameworks              = [],
                 platform                = None):
        """
        pre_include_bits: list of pieces of text that should be put at the top
        of the generated .c files, before any #include.  They shouldn't
        contain an #include themselves.  (Duplicate pieces are removed.)

        includes: list of .h file names to be #include'd from the
        generated .c files.

        include_dirs: list of dir names that is passed to the C compiler

        post_include_bits: list of pieces of text that should be put at the top
        of the generated .c files, after the #includes.  (Duplicate pieces are
        removed.)

        libraries: list of library names that is passed to the linker

        library_dirs: list of dir names that is passed to the linker

        separate_module_sources: list of multiline strings that are
        each written to a .c file and compiled separately and linked
        later on.  (If function prototypes are needed for other .c files
        to access this, they can be put in post_include_bits.)

        separate_module_files: list of .c file names that are compiled
        separately and linked later on.  (If an .h file is needed for
        other .c files to access this, it can be put in includes.)

        export_symbols: list of names that should be exported by the final
        binary.

        compile_extra: list of parameters which will be directly passed to
        the compiler

        link_extra: list of parameters which will be directly passed to
        the linker

        frameworks: list of Mac OS X frameworks which should passed to the
        linker. Use this instead of the 'libraries' parameter if you want to
        link to a framework bundle. Not suitable for unix-like .dylib
        installations.

        platform: an object that can identify the platform
        """
        for name in self._ATTRIBUTES:
            value = locals()[name]
            assert isinstance(value, (list, tuple))
            setattr(self, name, tuple(value))
        if platform is None:
            from pypy.translator.platform import platform
        self.platform = platform

    def from_compiler_flags(cls, flags):
        """Returns a new ExternalCompilationInfo instance by parsing
        the string 'flags', which is in the typical Unix compiler flags
        format."""
        pre_include_bits = []
        include_dirs = []
        compile_extra = []
        for arg in flags.split():
            if arg.startswith('-I'):
                include_dirs.append(arg[2:])
            elif arg.startswith('-D'):
                macro = arg[2:]
                if '=' in macro:
                    macro, value = macro.split('=')
                else:
                    value = '1'
                pre_include_bits.append('#define %s %s' % (macro, value))
            elif arg.startswith('-L') or arg.startswith('-l'):
                raise ValueError('linker flag found in compiler options: %r'
                                 % (arg,))
            else:
                compile_extra.append(arg)
        return cls(pre_include_bits=pre_include_bits,
                   include_dirs=include_dirs,
                   compile_extra=compile_extra)
    from_compiler_flags = classmethod(from_compiler_flags)

    def from_linker_flags(cls, flags):
        """Returns a new ExternalCompilationInfo instance by parsing
        the string 'flags', which is in the typical Unix linker flags
        format."""
        libraries = []
        library_dirs = []
        link_extra = []
        for arg in flags.split():
            if arg.startswith('-L'):
                library_dirs.append(arg[2:])
            elif arg.startswith('-l'):
                libraries.append(arg[2:])
            elif arg.startswith('-I') or arg.startswith('-D'):
                raise ValueError('compiler flag found in linker options: %r'
                                 % (arg,))
            else:
                link_extra.append(arg)
        return cls(libraries=libraries,
                   library_dirs=library_dirs,
                   link_extra=link_extra)
    from_linker_flags = classmethod(from_linker_flags)

    def from_config_tool(cls, execonfigtool):
        """Returns a new ExternalCompilationInfo instance by executing
        the 'execonfigtool' with --cflags and --libs arguments."""
        path = py.path.local.sysfind(execonfigtool)
        if not path:
            raise ImportError("cannot find %r" % (execonfigtool,))
            # we raise ImportError to be nice to the pypy.config.pypyoption
            # logic of skipping modules depending on non-installed libs
        cflags = py.process.cmdexec([str(path), '--cflags'])
        eci1 = cls.from_compiler_flags(cflags)
        libs = py.process.cmdexec([str(path), '--libs'])
        eci2 = cls.from_linker_flags(libs)
        return eci1.merge(eci2)
    from_config_tool = classmethod(from_config_tool)

    def _value(self):
        return tuple([getattr(self, x) for x in self._ATTRIBUTES]
                     + [self.platform])

    def __hash__(self):
        return hash(self._value())

    def __eq__(self, other):
        return self.__class__ is other.__class__ and \
               self._value() == other._value()

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        info = []
        for attr in self._ATTRIBUTES:
            val = getattr(self, attr)
            info.append("%s=%s" % (attr, repr(val)))
        info.append("platform=%s" % repr(self.platform))
        return "<ExternalCompilationInfo (%s)>" % ", ".join(info)

    def merge(self, *others):
        def unique_elements(l):
            seen = set()
            new_objs = []
            for obj in l:
                if obj not in seen:
                    new_objs.append(obj)
                    seen.add(obj)
            return new_objs
        others = unique_elements(list(others))

        attrs = {}
        for name in self._ATTRIBUTES:
            if name in self._DUPLICATES_OK:
                s = []
                for i in [self] + others:
                    s += getattr(i, name)
                attrs[name] = s
            else:
                s = set()
                attr = []
                for one in [self] + others:
                    for elem in getattr(one, name):
                        if elem not in s:
                            s.add(elem)
                            attr.append(elem)
                attrs[name] = attr
        for other in others:
            if other.platform != self.platform:
                raise Exception("Mixing ECI for different platforms %s and %s"%
                                (other.platform, self.platform))
        attrs['platform'] = self.platform
        return ExternalCompilationInfo(**attrs)

    def write_c_header(self, fileobj):
        for piece in self.pre_include_bits:
            print >> fileobj, piece
        for path in self.includes:
            print >> fileobj, '#include <%s>' % (path,)
        for piece in self.post_include_bits:
            print >> fileobj, piece

    def _copy_attributes(self):
        d = {}
        for attr in self._ATTRIBUTES:
            d[attr] = getattr(self, attr)
        return d

    def convert_sources_to_files(self, cache_dir=None, being_main=False):
        if not self.separate_module_sources:
            return self
        if cache_dir is None:
            cache_dir = udir.join('module_cache').ensure(dir=1)
        num = 0
        files = []
        for source in self.separate_module_sources:
            while 1:
                filename = cache_dir.join('module_%d.c' % num)
                num += 1
                if not filename.check():
                    break
            f = filename.open("w")
            if being_main:
                f.write("#define PYPY_NOT_MAIN_FILE\n")
            self.write_c_header(f)
            source = str(source)
            f.write(source)
            if not source.endswith('\n'):
                f.write('\n')
            f.close()
            files.append(str(filename))
        d = self._copy_attributes()
        d['separate_module_sources'] = ()
        d['separate_module_files'] += tuple(files)
        return ExternalCompilationInfo(**d)

    def compile_shared_lib(self):
        self = self.convert_sources_to_files()
        if not self.separate_module_files:
            return self
        lib = str(host.compile([], self, outputfilename='externmod',
                               standalone=False))
        d = self._copy_attributes()
        d['libraries'] += (lib,)
        d['separate_module_files'] = ()
        d['separate_module_sources'] = ()
        return ExternalCompilationInfo(**d)

if sys.platform == 'win32':
    so_ext = '.dll'
else:
    so_ext = '.so'

def compiler_command():
    # e.g. for tcc, you might set this to
    #    "tcc -shared -o %s.so %s.c"
    return os.getenv('PYPY_CC')

def enable_fast_compilation():
    if sys.platform == 'win32':
        dash = '/'
    else:
        dash = '-'
    from distutils import sysconfig
    gcv = sysconfig.get_config_vars()
    opt = gcv.get('OPT') # not always existent
    if opt:
        opt = re.sub('%sO\d+' % dash, '%sO0' % dash, opt)
    else:
        opt = '%sO0' % dash
    gcv['OPT'] = opt

def ensure_correct_math():
    if sys.platform != 'win32':
        return # so far
    from distutils import sysconfig
    gcv = sysconfig.get_config_vars()
    opt = gcv.get('OPT') # not always existent
    if opt and '/Op' not in opt:
        opt += '/Op'
    gcv['OPT'] = opt

def next_unique_name(modbasename, tmpdir):
    modname = modbasename
    while 1:
        if not tmpdir.join(modname + so_ext).check():
            break
        num += 1
        modname = '%s_%d' % (modbasename, num)
    return modname

def compile_c_module(cfiles, modbasename, eci, tmpdir=None):
    eci = eci.convert_sources_to_files()
    cfiles.extend(eci.separate_module_files)
    compiler = CCompiler(cfiles, eci, standalone=False)
    compiler.build()
    return str(compiler.outputfilename)

def make_module_from_c(cfile, eci):
    cfile = py.path.local(cfile)
    modname = cfile.purebasename
    compile_c_module([cfile], modname, eci)
    return import_module_from_directory(cfile.dirpath(), modname)

def import_module_from_directory(dir, modname):
    file, pathname, description = imp.find_module(modname, [str(dir)])
    try:
        mod = imp.load_module(modname, file, pathname, description)
    finally:
        if file:
            file.close()
    return mod


def log_spawned_cmd(spawn):
    def spawn_and_log(cmd, *args, **kwds):
        log.execute(' '.join(cmd))
        return spawn(cmd, *args, **kwds)
    return spawn_and_log


class CompilationError(Exception):
    pass

class CCompiler:
    fix_gcc_random_seed = False

    def __init__(self, cfilenames, eci, outputfilename=None,
                 compiler_exe=None, profbased=None, standalone=True):
        XXX
        self.cfilenames = cfilenames
        if standalone:
            ext = ''
        else:
            ext = so_ext
        self.standalone = standalone
        self.libraries = list(eci.libraries)
        self.include_dirs = list(eci.include_dirs)
        self.library_dirs = list(eci.library_dirs)
        self.compile_extra = list(eci.compile_extra)
        self.link_extra = list(eci.link_extra)
        self.frameworks = list(eci.frameworks)
        if compiler_exe is not None:
            self.compiler_exe = compiler_exe
        else:
            self.compiler_exe = eci.platform.get_compiler()
        self.profbased = profbased
        if not sys.platform in ('win32', 'darwin'): # xxx
            if 'm' not in self.libraries:
                self.libraries.append('m')
            self.compile_extra += CFLAGS + ['-fomit-frame-pointer']
            if 'pthread' not in self.libraries:
                self.libraries.append('pthread')
            if sys.platform != 'sunos5': 
                self.compile_extra += ['-pthread']
                self.link_extra += ['-pthread']
            else:
                self.compile_extra += ['-pthreads']
                self.link_extra += ['-lpthread']
        if sys.platform == 'win32':
            self.link_extra += ['/DEBUG'] # generate .pdb file
        if sys.platform == 'darwin':
            # support Fink & Darwinports
            for s in ('/sw/', '/opt/local/'):
                if s + 'include' not in self.include_dirs and \
                   os.path.exists(s + 'include'):
                    self.include_dirs.append(s + 'include')
                if s + 'lib' not in self.library_dirs and \
                   os.path.exists(s + 'lib'):
                    self.library_dirs.append(s + 'lib')
            self.compile_extra += CFLAGS + ['-fomit-frame-pointer']
            for framework in self.frameworks:
                self.link_extra += ['-framework', framework]

        if outputfilename is None:
            self.outputfilename = py.path.local(cfilenames[0]).new(ext=ext)
        else:
            self.outputfilename = py.path.local(outputfilename)
        self.eci = eci

    def build(self, noerr=False):
        import distutils.errors
        basename = self.outputfilename.new(ext='')
        data = ''
        try:
            saved_environ = os.environ.copy()
            try:
                c = stdoutcapture.Capture(mixed_out_err = True)
                if self.profbased is None:
                    self._build()
                else:
                    ProfDriver, args = self.profbased
                    profdrv = ProfDriver(self)
                    dolog = getattr(log, profdrv.name)
                    dolog(args)
                    profdrv.first()
                    dolog('Gathering profile data from: %s %s' % (
                           str(self.outputfilename), args))
                    profdrv.probe(str(self.outputfilename),args)
                    profdrv.after()
            finally:
                # workaround for a distutils bugs where some env vars can
                # become longer and longer every time it is used
                for key, value in saved_environ.items():
                    if os.environ.get(key) != value:
                        os.environ[key] = value
                foutput, foutput = c.done()
                data = foutput.read()
                if data:
                    fdump = basename.new(ext='errors').open("w")
                    fdump.write(data)
                    fdump.close()
        except (distutils.errors.CompileError,
                distutils.errors.LinkError), e:
            data = data.rstrip()
            if data:
                data += '\n'
            data += str(e)
            raise CompilationError(data)
        except:
            if not noerr:
                print >>sys.stderr, data
            raise

    def _build(self):
        from distutils.ccompiler import new_compiler
        from distutils import sysconfig
        compiler = new_compiler(force=1)
        if self.compiler_exe is not None:
            for c in '''compiler compiler_so compiler_cxx
                        linker_exe linker_so'''.split():
                compiler.executables[c][0] = self.compiler_exe
        if not self.standalone:
            sysconfig.customize_compiler(compiler) # XXX
        compiler.spawn = log_spawned_cmd(compiler.spawn)
        objects = []
        for cfile in self.cfilenames:
            cfile = py.path.local(cfile)
            compile_extra = self.compile_extra[:]
            # -frandom-seed is only to try to be as reproducable as possible
            if self.fix_gcc_random_seed:
                compile_extra.append('-frandom-seed=%s' % (cfile.basename,))
                # XXX horrible workaround for a bug of profiling in gcc on
                # OS X with functions containing a direct call to fork()
                if '/*--no-profiling-for-this-file!--*/' in cfile.read():
                    compile_extra = [arg for arg in compile_extra
                                     if not arg.startswith('-fprofile-')]

            old = cfile.dirpath().chdir()
            try:
                res = compiler.compile([cfile.basename],
                                       include_dirs=self.eci.include_dirs,
                                       extra_preargs=compile_extra)
                assert len(res) == 1
                cobjfile = py.path.local(res[0])
                assert cobjfile.check()
                objects.append(str(cobjfile))
            finally:
                old.chdir()

        if self.standalone:
            cmd = compiler.link_executable
        else:
            cmd = compiler.link_shared_object
        cmd(objects, str(self.outputfilename),
            libraries=self.eci.libraries,
            extra_preargs=self.link_extra,
            library_dirs=self.eci.library_dirs)

def check_under_under_thread():
    xxx
    from pypy.tool.udir import udir
    cfile = py.path.local(autopath.this_dir).join('__thread_test.c')
    fsource = cfile.open('r')
    source = fsource.read()
    fsource.close()
    cfile = udir.join('__thread_test.c')
    fsource = cfile.open('w')
    fsource.write(source)
    fsource.close()
    try:
       exe = build_executable([str(cfile)], ExternalCompilationInfo(),
                              noerr=True)
       py.process.cmdexec(exe)
    except (CompilationError,
            py.error.Error):
        return False
    else:
        return True
