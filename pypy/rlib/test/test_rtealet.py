import py
from pypy.translator.c.test.test_standalone import StandaloneTests


class BaseTestTealet(StandaloneTests):

    def setup_class(cls):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.gc = "minimark"
        config.translation.gcrootfinder = cls.gcrootfinder
        config.translation.tealet = True
        cls.config = config

    def test_demo1(self):
        from pypy.rlib.test.demotealet import entry_point
        t, cbuilder = self.compile(entry_point)

        expected_data = "Running...\nOK\n"
        for i in range(20):
            data = cbuilder.cmdexec('%d' % i, env={})
            assert data.endswith(expected_data)
            data = cbuilder.cmdexec('%d' % i, env={'PYPY_GC_NURSERY': '10k'})
            assert data.endswith(expected_data)


class TestTealetShadowstack(BaseTestTealet):
    gcrootfinder = "shadowstack"

class TestTealetAsmgcc(BaseTestTealet):
    gcrootfinder = "asmgcc"
