""" The tests below don't use translation at all.  They run the GCs by
instantiating them and asking them to allocate memory by calling their
methods directly.  The tests need to maintain by hand what the GC should
see as the list of roots (stack and prebuilt objects).
"""

# XXX VERY INCOMPLETE, low coverage

import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.gctypelayout import TypeLayoutBuilder

ADDR_ARRAY = lltype.Array(llmemory.Address)
S = lltype.GcForwardReference()
S.become(lltype.GcStruct('S',
                         ('x', lltype.Signed),
                         ('prev', lltype.Ptr(S)),
                         ('next', lltype.Ptr(S))))
RAW = lltype.Struct('RAW', ('p', lltype.Ptr(S)), ('q', lltype.Ptr(S)))


class DirectRootWalker(object):

    def __init__(self, tester):
        self.tester = tester

    def walk_roots(self, collect_stack_root,
                   collect_static_in_prebuilt_nongc,
                   collect_static_in_prebuilt_gc):
        gc = self.tester.gc
        layoutbuilder = self.tester.layoutbuilder
        if collect_static_in_prebuilt_gc:
            for addrofaddr in layoutbuilder.addresses_of_static_ptrs:
                if addrofaddr.address[0]:
                    collect_static_in_prebuilt_gc(gc, addrofaddr)
        if collect_static_in_prebuilt_nongc:
            for addrofaddr in layoutbuilder.addresses_of_static_ptrs_in_nongc:
                if addrofaddr.address[0]:
                    collect_static_in_prebuilt_nongc(gc, addrofaddr)
        if collect_stack_root:
            stackroots = self.tester.stackroots
            a = lltype.malloc(ADDR_ARRAY, len(stackroots), flavor='raw')
            for i in range(len(a)):
                a[i] = llmemory.cast_ptr_to_adr(stackroots[i])
            a_base = lltype.direct_arrayitems(a)
            for i in range(len(a)):
                ai = lltype.direct_ptradd(a_base, i)
                collect_stack_root(gc, llmemory.cast_ptr_to_adr(ai))
            for i in range(len(a)):
                PTRTYPE = lltype.typeOf(stackroots[i])
                stackroots[i] = llmemory.cast_adr_to_ptr(a[i], PTRTYPE)
            lltype.free(a, flavor='raw')

    def _walk_prebuilt_gc(self, callback):
        pass


class DirectGCTest(object):
    GC_PARAMS = {}

    def setup_method(self, meth):
        self.stackroots = []
        self.gc = self.GCClass(**self.GC_PARAMS)
        self.gc.DEBUG = True
        self.rootwalker = DirectRootWalker(self)
        self.gc.set_root_walker(self.rootwalker)
        self.layoutbuilder = TypeLayoutBuilder()
        self.get_type_id = self.layoutbuilder.get_type_id
        self.layoutbuilder.initialize_gc_query_function(self.gc)
        self.gc.setup()

    def consider_constant(self, p):
        obj = p._obj
        TYPE = lltype.typeOf(obj)
        self.layoutbuilder.consider_constant(TYPE, obj, self.gc)

    def write(self, p, fieldname, newvalue):
        if self.gc.needs_write_barrier:
            oldaddr = llmemory.cast_ptr_to_adr(getattr(p, fieldname))
            newaddr = llmemory.cast_ptr_to_adr(newvalue)
            addr_struct = llmemory.cast_ptr_to_adr(p)
            self.gc.write_barrier(oldaddr, newaddr, addr_struct)
        setattr(p, fieldname, newvalue)

    def malloc(self, TYPE):
        addr = self.gc.malloc(self.get_type_id(TYPE))
        return llmemory.cast_adr_to_ptr(addr, lltype.Ptr(TYPE))

    def test_simple(self):
        p = self.malloc(S)
        p.x = 5
        self.stackroots.append(p)
        self.gc.collect()
        p = self.stackroots[0]
        assert p.x == 5

    def test_missing_stack_root(self):
        p = self.malloc(S)
        p.x = 5
        self.gc.collect()    # 'p' should go away
        py.test.raises(RuntimeError, 'p.x')

    def test_prebuilt_gc(self):
        k = lltype.malloc(S, immortal=True)
        k.x = 42
        self.consider_constant(k)
        self.write(k, 'next', self.malloc(S))
        k.next.x = 43
        self.write(k.next, 'next', self.malloc(S))
        k.next.next.x = 44
        self.gc.collect()
        assert k.x == 42
        assert k.next.x == 43
        assert k.next.next.x == 44

    def test_prebuilt_nongc(self):
        raw = lltype.malloc(RAW, immortal=True)
        self.consider_constant(raw)
        raw.p = self.malloc(S)
        raw.p.x = 43
        raw.q = self.malloc(S)
        raw.q.x = 44
        self.gc.collect()
        assert raw.p.x == 43
        assert raw.q.x == 44

    def test_many_objects(self):

        def alloc2(i):
            a1 = self.malloc(S)
            a1.x = i
            self.stackroots.append(a1)
            a2 = self.malloc(S)
            a1 = self.stackroots.pop()
            a2.x = i + 1000
            return a1, a2

        def growloop(loop, a1, a2):
            self.write(a1, 'prev', loop.prev)
            self.write(a1.prev, 'next', a1)
            self.write(a1, 'next', loop)
            self.write(loop, 'prev', a1)
            self.write(a2, 'prev', loop)
            self.write(a2, 'next', loop.next)
            self.write(a2.next, 'prev', a2)
            self.write(loop, 'next', a2)

        def newloop():
            p = self.malloc(S)
            p.next = p          # initializing stores, no write barrier
            p.prev = p
            return p

        # a loop attached to a stack root
        self.stackroots.append(newloop())

        # another loop attached to a prebuilt gc node
        k = lltype.malloc(S, immortal=True)
        k.next = k
        k.prev = k
        self.consider_constant(k)

        # a third loop attached to a prebuilt nongc
        raw = lltype.malloc(RAW, immortal=True)
        self.consider_constant(raw)
        raw.p = newloop()

        # run!
        for i in range(100):
            a1, a2 = alloc2(i)
            growloop(self.stackroots[0], a1, a2)
            a1, a2 = alloc2(i)
            growloop(k, a1, a2)
            a1, a2 = alloc2(i)
            growloop(raw.p, a1, a2)


class TestSemiSpaceGC(DirectGCTest):
    from pypy.rpython.memory.gc.semispace import SemiSpaceGC as GCClass

class TestGenerationGC(TestSemiSpaceGC):
    from pypy.rpython.memory.gc.generation import GenerationGC as GCClass

class TestHybridGC(TestGenerationGC):
    from pypy.rpython.memory.gc.hybrid import HybridGC as GCClass
