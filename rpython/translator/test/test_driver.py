import py
import os

from rpython.translator.driver import TranslationDriver
from rpython.translator.interactive import Translation
from rpython.tool.udir import udir


def test_c_no_jit():
    td = TranslationDriver()
    td.setup(None, None)
    names = ['annotate', 'rtype', 'backendopt', 'stackcheckinsertion',
             'transform', 'database', 'source', 'compile']
    assert [task.task_name for task in td.tasks] == names


def test_c_with_jit():
    td = TranslationDriver({'jit': True})
    td.setup(None, None)
    names = ['annotate', 'rtype', 'pyjitpl', 'backendopt',
             'stackcheckinsertion', 'transform', 'database', 'source',
             'compile']
    assert [task.task_name for task in td.tasks] == names


def test_no_backendopt():
    td = TranslationDriver({'backendopt.none': True})
    td.setup(None, None)
    names = ['annotate', 'rtype', 'stackcheckinsertion', 'transform',
             'database', 'source', 'compile']
    assert [task.task_name for task in td.tasks] == names


def test_simple_annotate():
    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    s = t.annotate()
    assert s.knowntype == int
    assert 'annotate' in t.driver.done
    assert t.context is t.driver.translator
    assert t.config is t.driver.config is t.context.config

def test_simple_rtype():
    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    t.rtype()
    assert 'annotate' in t.driver.done
    assert 'rtype' in t.driver.done

def test_simple_backendopt():
    def f(x, y):
        return x,y

    t = Translation(f, [int, int], backend='c')
    t.backendopt()

    assert 'backendopt' in t.driver.done

def test_simple_source():
    def f(x, y):
        return x,y

    t = Translation(f, [int, int], backend='c')
    t.annotate()
    t.source()
    assert 'source' in t.driver.done

    t = Translation(f, [int, int])
    t.source()
    assert 'source' in t.driver.done

def test_disable_logic():
    def f(x,y):
        return x+y

    t = Translation(f, [int, int], **{'backendopt.none': True})
    t.source()

    assert 'backendopt' not in t.driver.done

def test_simple_compile_c():
    import ctypes

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    t.source()
    t.compile()

    dll = ctypes.CDLL(str(t.driver.c_entryp))
    f = dll.pypy_g_f
    assert f(2, 3) == 5


def test_create_exe():
    if not os.name == 'nt':
        py.test.skip('Windows only test')

    dst_name = udir.join('dst/pypy.exe')
    src_name = udir.join('src/dydy2.exe')
    dll_name = udir.join('src/pypy.dll')
    lib_name = udir.join('src/pypy.lib')
    src_name.ensure()
    src_name.write('exe')
    dll_name.ensure()
    dll_name.write('dll')
    lib_name.ensure()
    lib_name.write('lib')
    dst_name.ensure()

    class CBuilder(object):
        shared_library_name = dll_name

    td = TranslationDriver(exe_name=str(dst_name))
    td.c_entryp = str(src_name)
    td.cbuilder = CBuilder()
    td.create_exe()
    assert dst_name.read() == 'exe'
    assert dst_name.new(ext='dll').read() == 'dll'
    assert dst_name.new(purebasename='python27',ext='lib').read() == 'lib'
