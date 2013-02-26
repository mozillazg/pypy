from rpython.translator.driver import TranslationDriver
from rpython.translator.interactive import Translation


def test_c_no_jit():
    td = TranslationDriver()
    names = ['annotate', 'rtype', 'backendopt', 'stackcheckinsertion_lltype',
             'database', 'source', 'compile']
    assert [task.task_name for task in td.tasks] == names


def test_c_with_jit():
    td = TranslationDriver({'jit': True})
    names = ['annotate', 'rtype', 'pyjitpl', 'backendopt',
             'stackcheckinsertion_lltype', 'database', 'source', 'compile']
    assert [task.task_name for task in td.tasks] == names


def test_no_backendopt():
    td = TranslationDriver({'backendopt.none': True})
    names = ['annotate', 'rtype', 'stackcheckinsertion_lltype', 'database',
             'source', 'compile']
    assert [task.task_name for task in td.tasks] == names


def test_simple_annotate():

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    assert t.context is t.driver.translator
    assert t.config is t.driver.config is t.context.config
    
    s = t.annotate()
    assert s.knowntype == int

    t = Translation(f, [int, int])
    s = t.annotate()
    assert s.knowntype == int


def test_simple_rtype():

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    t.annotate()
    t.rtype()

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
    return # temporary skip

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    t.disable(['backendopt'])
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

def test_simple_rtype_with_type_system():

    def f(x,y):
        return x+y

    t = Translation(f, [int, int])
    t.rtype()

    t = Translation(f, [int, int], type_system='ootype')
    t.rtype()
    assert 'rtype' in t.driver.done

    t = Translation(f, [int, int], backend='cli', type_system='ootype')
    t.rtype()
    assert 'rtype' in t.driver.done
