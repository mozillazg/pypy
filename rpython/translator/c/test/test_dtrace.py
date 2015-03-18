
import subprocess, py, sys
from rpython.translator.c.test.test_standalone import StandaloneTests
from rpython.rlib.debug import debug_start, debug_stop
from rpython.config.translationoption import get_combined_translation_config
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.lltypesystem import lltype

class TestDTrace(StandaloneTests):
    config = get_combined_translation_config(translating=True)
    config.translation.dtrace = True

    def setup_class(cls):
        if not (sys.platform.startswith('freebsd') or
                sys.platform.startswith('darwin')):
            py.test.skip("not supported on other platforms")
    
    def test_dtrace_probes(self):
        def f(argv):
            debug_start("x")
            for i in range(10000000):
                pass
            debug_stop("x")
            return 0

        _, cbuilder = self.compile(f)
        exe = cbuilder.executable_name
        p = subprocess.Popen(['dtrace', '-n', ':' + exe.basename + '::',
                              '-c', str(exe)], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        out = p.stdout.read()
        assert 'pypy_g_f:x-start' in out
        assert 'pypy_g_f:x-end' in out

    def test_debug_probe(self):
        def f(argv):
            llop.debug_probe(lltype.Void, "foo", 13)
            return 0

        _, cbuilder = self.compile(f)
        exe = cbuilder.executable_name
        p = subprocess.Popen(['dtrace', '-n', ':' + exe.basename + '::',
                              '-c', str(exe)], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        out = p.stdout.read()
        assert 'pypy_g_f:foo' in out
