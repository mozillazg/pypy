
import py
from rpython.translator.backendopt.destructor import DestructorAnalyzer,\
     DestructorError
from rpython.translator.translator import TranslationContext, graphof
from rpython.translator.backendopt.all import backend_optimizations
from rpython.translator.unsimplify import varoftype
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.conftest import option
from rpython.rlib import rgc


class TestDestructorAnalyzer(object):
    """ Below are typical destructors that we encounter in pypy
    """

    def analyze(self, func, sig, func_to_analyze=None, backendopt=False):
        if func_to_analyze is None:
            func_to_analyze = func
        t = TranslationContext()
        t.buildannotator().build_types(func, sig)
        t.buildrtyper().specialize()
        if backendopt:
            backend_optimizations(t)
        if option.view:
            t.view()
        a = DestructorAnalyzer(t)
        fgraph = graphof(t, func_to_analyze)
        result = a.analyze_direct_call(fgraph)
        return result

    def test_nothing(self):
        def f():
            pass
        r = self.analyze(f, [])
        assert not r

def test_various_ops():
    from rpython.flowspace.model import SpaceOperation, Constant

    X = lltype.Ptr(lltype.GcStruct('X'))
    Z = lltype.Ptr(lltype.Struct('Z'))
    S = lltype.GcStruct('S', ('x', lltype.Signed),
                        ('y', X),
                        ('z', Z))
    v1 = varoftype(lltype.Bool)
    v2 = varoftype(lltype.Signed)
    f = DestructorAnalyzer(None)
    r = f.analyze(SpaceOperation('cast_int_to_bool', [v2],
                                                       v1))
    assert not r
    v1 = varoftype(lltype.Ptr(S))
    v2 = varoftype(lltype.Signed)
    v3 = varoftype(X)
    v4 = varoftype(Z)
    assert not f.analyze(SpaceOperation('bare_setfield', [v1, Constant('x'),
                                                          v2], None))
    assert     f.analyze(SpaceOperation('bare_setfield', [v1, Constant('y'),
                                                          v3], None))
    assert not f.analyze(SpaceOperation('bare_setfield', [v1, Constant('z'),
                                                          v4], None))

    def test_malloc(self):
        S = lltype.GcStruct('S')

        def f():
            return lltype.malloc(S)

        r = self.analyze(f, [])
        assert r

    def test_raw_free_getfield(self):
        S = lltype.Struct('S')

        class A(object):
            def __init__(self):
                self.x = lltype.malloc(S, flavor='raw')

            def __del__(self):
                if self.x:
                    lltype.free(self.x, flavor='raw')
                    self.x = lltype.nullptr(S)

        def f():
            return A()

        r = self.analyze(f, [], A.__del__.im_func)
        assert not r

    def test_c_call(self):
        C = rffi.CArray(lltype.Signed)
        c = rffi.llexternal('x', [lltype.Ptr(C)], lltype.Signed)

        def g():
            p = lltype.malloc(C, 3, flavor='raw')
            f(p)

        def f(p):
            c(rffi.ptradd(p, 0))
            lltype.free(p, flavor='raw')

        r = self.analyze(g, [], f, backendopt=True)
        assert not r

    def test_c_call_2(self):
        X = lltype.Ptr(lltype.Struct('X'))
        x = rffi.llexternal('x', [X], lltype.Signed, threadsafe=True)
        class C(object):
            lib = rffi.cast(X, -1)

        def g():
            c = C()
            c.lib = rffi.cast(X, -2)
            f(c)

        def f(c):
            if c.lib != rffi.cast(X, -1):
                x(c.lib)
                c.lib = rffi.cast(X, -1)

        r = self.analyze(g, [], f, backendopt=True)
        assert not r

    def test_setarrayitem(self):
        x = lltype.malloc(lltype.Array(lltype.Signed), 5, flavor='raw',
                          immortal=True)
        def f():
            x[1] += 1

        r = self.analyze(f, [], f)
        assert not r

    def test_chain(self):
        class B(object):
            def __init__(self):
                self.counter = 1

        class A(object):
            def __init__(self):
                self.x = B()

            def __del__(self):
                self.x.counter += 1

        def f():
            A()

        r = self.analyze(f, [], A.__del__.im_func)
        assert r
