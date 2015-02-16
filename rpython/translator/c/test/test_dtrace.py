
from rpython.translator.c.test.test_standalone import StandaloneTests
from rpython.rlib.debug import debug_start, debug_stop
from rpython.config.translationoption import get_combined_translation_config

class TestDTrace(StandaloneTests):
    config = get_combined_translation_config(translating=True)
    config.translation.dtrace = True
    
    def test_dtrace_probes(self):
        def f(argv):
            debug_start("x")
            for i in range(10000000):
                pass
            debug_stop("x")
            return 0

        _, cbuilder = self.compile(f)
        cbuilder.cmdexec('')
