
import py
import sys
from pypy.conftest import gettestobjspace
from pypy.tool.autopath import pypydir

def setup_module(mod):
    try:
        import pexpect
        mod.pexpect = pexpect
    except ImportError:
        py.test.skip("Pexpect not found")
    try:
        import termios
        mod.termios = termios
    except ImportError:
        py.test.skip("termios not found")
    py_py = py.path.local(pypydir).join('bin', 'py.py')
    assert py_py.check()
    mod.py_py = py_py

class TestTermios(object):
    def _spawn(self, *args, **kwds):
        print 'SPAWN:', args, kwds
        child = pexpect.spawn(*args, **kwds)
        child.logfile = sys.stdout
        return child

    def spawn(self, argv):
        return self._spawn(sys.executable, [str(py_py)] + argv)

    def test_one(self):
        child = self.spawn(['--withmod-termios'])
        child.expect("Python ")
        child.expect('>>> ')
        child.sendline('import termios')
        child.expect('>>> ')
        child.sendline('termios.tcgetattr(0)')
        child.expect('\[.*?\[.*?\]\]')
        lst = eval(child.match.group(0))
        assert len(lst) == 7
        assert len(lst[-1]) == 32 # XXX is this portable???

class AppTestTermios(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['termios'])
        d = {}
        for name in dir(termios):
            val = getattr(termios, name)
            if name.isupper() and type(val) is int:
                d[name] = val
        cls.w_orig_module_dict = cls.space.appexec([], "(): return %r" % (d,))

    def test_values(self):
        import termios
        d = {}
        for name in dir(termios):
            val = getattr(termios, name)
            if name.isupper() and type(val) is int:
                d[name] = val
        assert d == self.orig_module_dict

    def test_error(self):
        # XXX not always true, but good assumption
        import termios
        raises(termios.error, "termios.tcgetattr(334)")
