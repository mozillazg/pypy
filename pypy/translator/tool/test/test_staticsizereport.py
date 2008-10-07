from pypy.translator.c.test.test_typed import CompilationTestCase
from pypy.translator.tool.staticsizereport import group_static_size, guess_size

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
        size, num = group_static_size(self.builder.db, self.builder.db.globalcontainers())
        for key, value in num.iteritems():
            if "staticsizereport.A" in str(key) and "vtable" not in str(key):
                assert value == 101

    def test_large_dict(self):
        d = {}
        class wrap:
            pass
        for x in xrange(100):
            i = wrap()
            i.x = x
            d[x] = i
        def f(x):
            return d[x].x
        func = self.getcompiled(f, [int])
        gcontainers = self.builder.db.globalcontainers()
        dictvalnode = [node for node in gcontainers if "struct dicttable" in repr(node.obj)][0]
        assert guess_size(self.builder.db, dictvalnode, set()) > 100
        size, num = group_static_size(self.builder.db, gcontainers)
        1/0
