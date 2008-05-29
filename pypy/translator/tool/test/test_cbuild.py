import py, sys

from pypy.tool.udir import udir 
from pypy.translator.tool.cbuild import build_executable, \
     ExternalCompilationInfo, CompilationSet, compile_c_module
from subprocess import Popen, PIPE, STDOUT

def test_simple_executable(): 
    print udir
    testpath = udir.join('testbuildexec')
    t = testpath.ensure("test.c")
    t.write(r"""
        #include <stdio.h>
        int main() {
            printf("hello world\n");
            return 0;
        }
""")
    eci = ExternalCompilationInfo()
    testexec = build_executable([t], eci)
    out = py.process.cmdexec(testexec)
    assert out.startswith('hello world')

class TestEci:
    def setup_class(cls):
        tmpdir = udir.ensure('testeci', dir=1)
        c_file = tmpdir.join('module.c')
        c_file.write(py.code.Source('''
        int sum(int x, int y)
        {
            return x + y;
        }
        '''))
        cls.modfile = c_file
        cls.tmpdir = tmpdir

    def test_standalone(self):
        tmpdir = self.tmpdir
        c_file = tmpdir.join('stand1.c')
        c_file.write('''
        #include <math.h>
        #include <stdio.h>
        
        int main()
        {
            printf("%f\\n", pow(2.0, 2.0));
        }''')
        if sys.platform != 'win32':
            eci = ExternalCompilationInfo(
                libraries = ['m'],
                )
        else:
            eci = ExternalCompilationInfo()
        output = build_executable([c_file], eci)
        p = Popen(output, stdout=PIPE, stderr=STDOUT)
        p.wait()
        assert p.stdout.readline().startswith('4.0')
    
    def test_merge(self):
        e1 = ExternalCompilationInfo(
            pre_include_lines  = ['1'],
            includes           = ['x.h'],
            post_include_lines = ['p1']
        )
        e2 = ExternalCompilationInfo(
            pre_include_lines  = ['2'],
            includes           = ['x.h', 'y.h'],
            post_include_lines = ['p2'],
        )
        e3 = ExternalCompilationInfo(
            pre_include_lines  = ['3'],
            includes           = ['y.h', 'z.h'],
            post_include_lines = ['p3']
        )
        e = e1.merge(e2, e3)
        assert e.pre_include_lines == ('1', '2', '3')
        assert e.includes == ('x.h', 'y.h', 'z.h')
        assert e.post_include_lines == ('p1', 'p2', 'p3')

    def test_merge2(self):
        e1 = ExternalCompilationInfo(
            pre_include_lines  = ['1'],
        )
        e2 = ExternalCompilationInfo(
            pre_include_lines  = ['2'],
        )
        e3 = ExternalCompilationInfo(
            pre_include_lines  = ['3'],
        )
        e = e1.merge(e2)
        e = e.merge(e3, e3)
        assert e.pre_include_lines == ('1', '2', '3')

    def test_convert_sources_to_c_files(self):
        cs = CompilationSet(
            ExternalCompilationInfo(),
            sources = ['xxx'],
            files = ['x.c'],
        )
        cache_dir = udir.join('test_convert_sources').ensure(dir=1)
        newcs = cs.convert_sources_to_files(cache_dir)
        assert not newcs.sources
        res = newcs.files
        assert len(res) == 2
        assert res[0] == 'x.c'
        assert str(res[1]).startswith(str(cache_dir))
        cs = CompilationSet(ExternalCompilationInfo())
        assert cs.convert_sources_to_files() is cs

    def test_make_shared_lib(self):
        eci = ExternalCompilationInfo(
            separate_module_sources = ['''
            int get()
            {
                return 42;
            }'''],
            export_symbols = ['get']
        )
        neweci = eci.compile_shared_lib()
        assert len(neweci.libraries) == 1
        try:
            import ctypes
        except ImportError:
            py.test.skip("Need ctypes for that test")
        assert ctypes.CDLL(neweci.libraries[0]).get() == 42
        assert not neweci.separate_module_sources
        assert not neweci.separate_module_files

    def test_from_compiler_flags(self):
        flags = ('-I/some/include/path -I/other/include/path '
                 '-DMACRO1 -D_MACRO2=baz -?1 -!2')
        eci = ExternalCompilationInfo.from_compiler_flags(flags)
        assert eci.pre_include_lines == ('#define MACRO1 1',
                                         '#define _MACRO2 baz')
        assert eci.includes == ()
        assert eci.include_dirs == ('/some/include/path',
                                    '/other/include/path')
        assert eci.compile_extra == ('-?1', '-!2')

    def test_from_linker_flags(self):
        flags = ('-L/some/lib/path -L/other/lib/path '
                 '-lmylib1 -lmylib2 -?1 -!2')
        eci = ExternalCompilationInfo.from_linker_flags(flags)
        assert eci.libraries == ('mylib1', 'mylib2')
        assert eci.library_dirs == ('/some/lib/path',
                                    '/other/lib/path')
        assert eci.link_extra == ('-?1', '-!2')

    def test_from_config_tool(self):
        sdlconfig = py.path.local.sysfind('sdl-config')
        if not sdlconfig:
            py.test.skip("sdl-config not installed")
        eci = ExternalCompilationInfo.from_config_tool('sdl-config')
        assert 'SDL' in eci.libraries

    def test_from_missing_config_tool(self):
        py.test.raises(ImportError,
                       ExternalCompilationInfo.from_config_tool,
                       'dxowqbncpqympqhe-config')
