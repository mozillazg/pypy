import py
from pypy.rpython.memory.gctransform.test.test_transform import rtype, rtype_and_transform, getops
from pypy.rpython.memory.gctransform.test.test_transform import LLInterpedTranformerTests
from pypy.rpython.memory.gctransform.refcounting import RefcountingGCTransformer
from pypy.rpython.lltypesystem import lltype
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.c.gc import RefcountingGcPolicy
from pypy import conftest

class TestLLInterpedRefcounting(LLInterpedTranformerTests):
    gcpolicy = RefcountingGcPolicy

    def test_llinterp_refcounted_graph_with_del(self):
        from pypy.annotation.model import SomeInteger

        class D:
            pass

        delcounter = D()
        delcounter.dels = 0

        class C:
            def __del__(self):
                delcounter.dels += 1
        c = C()
        c.x = 1
        def h(x):
            if x:
                return c
            else:
                d = C()
                d.x = 2
                return d
        def g(x):
            return h(x).x
        def f(x):
            r = g(x)
            return r + delcounter.dels

        llinterp, graph = self.llinterpreter_for_transformed_graph(f, [SomeInteger()])

        res = llinterp.eval_graph(graph, [1])
        assert res == 1
        res = llinterp.eval_graph(graph, [0])
        assert res == 3

    def test_raw_instance_flavor(self):
        # crashes for now because X() is not initialized with zeroes when
        # it is allocated, but it's probably illegal to try to store
        # references into a raw-malloced instance
        py.test.skip("a probably-illegal test")
        class State:
            pass
        state = State()
        class Y:
            def __del__(self):
                state.freed_counter += 1
        class X:
            _alloc_flavor_ = 'raw'
        def g():
            x = X()
            x.y = Y()
            return x
        def f():
            from pypy.rlib.objectmodel import free_non_gc_object
            state.freed_counter = 0
            x = g()
            assert state.freed_counter == 0
            x.y = None
            assert state.freed_counter == 1
            free_non_gc_object(x)
            # for now we have no automatic decref when free_non_gc_object() is
            # called
        llinterp, graph = self.llinterpreter_for_transformed_graph(f, [])
        llinterp.eval_graph(graph, [])

def test_simple_barrier():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    T = lltype.GcStruct("T", ('s', lltype.Ptr(S)))
    def f():
        s1 = lltype.malloc(S)
        s1.x = 1
        s2 = lltype.malloc(S)
        s2.x = 2
        t = lltype.malloc(T)
        t.s = s1
        t.s = s2
        return t
    t, transformer = rtype_and_transform(f, [], RefcountingGCTransformer,
                                         check=False)
    graph = graphof(t, f)
    ops = getops(graph)
    assert len(ops['getfield']) == 2
    assert len(ops['bare_setfield']) == 4

def test_arraybarrier():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    A = lltype.GcArray(lltype.Ptr(S))
    def f():
        s1 = lltype.malloc(S)
        s1.x = 1
        s2 = lltype.malloc(S)
        s2.x = 2
        a = lltype.malloc(A, 1)
        a[0] = s1
        a[0] = s2
    t, transformer = rtype_and_transform(f, [], RefcountingGCTransformer,
                                         check=False)
    graph = graphof(t, f)
    ops = getops(graph)
    assert len(ops['getarrayitem']) == 2
    assert len(ops['bare_setarrayitem']) == 2
    assert len(ops['bare_setfield']) == 2

def make_deallocator(TYPE,
                     attr="static_deallocation_funcptr_for_type",
                     cls=RefcountingGCTransformer):
    if TYPE._is_varsize():
        def f():
            return lltype.malloc(TYPE, 1)
    else:
        def f():
            return lltype.malloc(TYPE)
    t = TranslationContext()
    t.buildannotator().build_types(f, [])
    t.buildrtyper().specialize()
    transformer = cls(t)
    fptr = getattr(transformer, attr)(TYPE)
    transformer.transform_graph(graphof(t, f))
    transformer.finish(backendopt=False)
    if conftest.option.view:
        t.view()
    if fptr:
        return fptr._obj.graph, t
    else:
        return None, t

def test_deallocator_simple():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    dgraph, t = make_deallocator(S)
    ops = []
    for block in dgraph.iterblocks():
        ops.extend([op for op in block.operations if op.opname != 'same_as']) # XXX
    assert len(ops) == 1
    op = ops[0]
    assert op.opname == 'raw_free'

def test_deallocator_less_simple():
    TPtr = lltype.Ptr(lltype.GcStruct("T", ('a', lltype.Signed)))
    S = lltype.GcStruct(
        "S",
        ('x', lltype.Signed),
        ('y', TPtr),
        ('z', TPtr),
        )
    dgraph, t = make_deallocator(S)
    ops = getops(dgraph)
    assert len(ops['direct_call']) == 2
    assert len(ops['getfield']) == 2
    assert len(ops['raw_free']) == 1

def test_deallocator_array():
    TPtr = lltype.Ptr(lltype.GcStruct("T", ('a', lltype.Signed)))
    GcA = lltype.GcArray(('x', TPtr), ('y', TPtr))
    A = lltype.Array(('x', TPtr), ('y', TPtr))
    APtr = lltype.Ptr(GcA)
    S = lltype.GcStruct('S', ('t', TPtr), ('x', lltype.Signed), ('aptr', APtr),
                             ('rest', A))
    dgraph, t = make_deallocator(S)
    ops = getops(dgraph)
    assert len(ops['direct_call']) == 4
    assert len(ops['getfield']) == 2
    assert len(ops['getinteriorfield']) == 2
    assert len(ops['getinteriorarraysize']) == 1
    assert len(ops['raw_free']) == 1

def test_deallocator_with_destructor():
    pinf = lltype.malloc(lltype.RuntimeTypeInfo, immortal=True)
    S = lltype.GcStruct("S", ('x', lltype.Signed), runtime_type_info=pinf)
    def f(s):
        s.x = 1
    dp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Void),
                            "destructor_funcptr",
                            _callable=f)
    pinf.destructor_funcptr = dp
    graph, t = make_deallocator(S)

def test_recursive_structure():
    F = lltype.GcForwardReference()
    S = lltype.GcStruct('abc', ('x', lltype.Ptr(F)))
    F.become(S)
    def f():
        s1 = lltype.malloc(S)
        s2 = lltype.malloc(S)
        s1.x = s2
    t, transformer = rtype_and_transform(
        f, [], RefcountingGCTransformer, check=False)

def test_dont_decref_nongc_pointers():
    S = lltype.GcStruct('S',
                        ('x', lltype.Ptr(lltype.Struct('T', ('x', lltype.Signed)))),
                        ('y', lltype.Ptr(lltype.GcStruct('Y', ('x', lltype.Signed))))
                        )
    def f():
        pass
    graph, t = make_deallocator(S)
    ops = getops(graph)
    assert len(ops['direct_call']) == 1
