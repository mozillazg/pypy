from pypy.translator.c.test.test_typed import CompilationTestCase
from pypy.translator.tool.staticsizereport import group_static_size_by_lltype

class TestStaticSizeReport(CompilationTestCase):
    def test_simple(self):
        class A:
            def __init__(self, n):
                if n:
                    self.next = A(n - 1)
                else:
                    self.next = None
                self.key = repr(self)
        a = A(100)
        def f(x):
            if x:
                return a.key
            return a.next.key
        func = self.getcompiled(f, [int])
        size, num = group_static_size_by_lltype(self.builder.db)
        for key, value in num.iteritems():
            if "staticsizereport.A" in str(key) and "vtable" not in str(key):
                assert value == 101

