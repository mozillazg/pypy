import py
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.memory.gc.incminimark import IncrementalMiniMarkGC
from rpython.memory.gc.test.test_direct import BaseDirectGCTest
from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY
from rpython.rlib.rawrefcount import REFCNT_FROM_PYPY_DIRECT

PYOBJ_HDR = IncrementalMiniMarkGC.PYOBJ_HDR
PYOBJ_HDR_PTR = IncrementalMiniMarkGC.PYOBJ_HDR_PTR

S = lltype.GcForwardReference()
S.become(lltype.GcStruct('S',
                         ('x', lltype.Signed),
                         ('prev', lltype.Ptr(S)),
                         ('next', lltype.Ptr(S))))


class TestRawRefCount(BaseDirectGCTest):
    GCClass = IncrementalMiniMarkGC

    def _rawrefcount_pair(self, intval, is_direct=False, is_pyobj=False):
        if is_direct:
            rc = REFCNT_FROM_PYPY_DIRECT
        else:
            rc = REFCNT_FROM_PYPY
        #
        p1 = self.malloc(S)
        p1.x = intval
        p1ref = lltype.cast_opaque_ptr(llmemory.GCREF, p1)
        r1 = lltype.malloc(PYOBJ_HDR, flavor='raw')
        r1.ob_refcnt = rc
        r1.ob_pypy_link = 0
        r1addr = llmemory.cast_ptr_to_adr(r1)
        self.dealloc = []
        self.gc.rawrefcount_init(self.dealloc.append)
        if is_pyobj:
            assert not is_direct
            self.gc.rawrefcount_create_link_pyobj(p1ref, r1addr)
        else:
            self.gc.rawrefcount_create_link_pypy(p1ref, r1addr)
        assert r1.ob_refcnt == rc
        assert r1.ob_pypy_link != 0

        def check_alive(extra_refcount):
            assert r1.ob_refcnt == rc + extra_refcount
            assert r1.ob_pypy_link != 0
            p1ref = self.gc.rawrefcount_to_obj(r1addr)
            p1 = lltype.cast_opaque_ptr(lltype.Ptr(S), p1ref)
            assert p1.x == 42
            assert self.gc.rawrefcount_from_obj(p1ref) == r1addr
            return p1
        return p1, p1ref, r1, r1addr, check_alive

    def test_rawrefcount_objects_basic(self):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_direct=True))
        p2 = self.malloc(S)
        p2.x = 84
        p2ref = lltype.cast_opaque_ptr(llmemory.GCREF, p2)
        r2 = lltype.malloc(PYOBJ_HDR, flavor='raw')
        r2.ob_refcnt = 1
        r2.ob_pypy_link = 0
        r2addr = llmemory.cast_ptr_to_adr(r2)
        # p2 and r2 are not linked
        assert r1.ob_pypy_link != 0
        assert r2.ob_pypy_link == 0
        assert self.gc.rawrefcount_from_obj(p1ref) == r1addr
        assert self.gc.rawrefcount_from_obj(p2ref) == llmemory.NULL
        assert self.gc.rawrefcount_to_obj(r1addr) == p1ref
        assert self.gc.rawrefcount_to_obj(r2addr) == lltype.nullptr(
            llmemory.GCREF.TO)
        lltype.free(r1, flavor='raw')
        lltype.free(r2, flavor='raw')

    def test_rawrefcount_objects_collection_survives_from_raw(self):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_direct=True))
        check_alive(0)
        r1.ob_refcnt += 1
        self.gc.minor_collection()
        check_alive(+1)
        self.gc.collect()
        check_alive(+1)
        r1.ob_refcnt -= 1
        self.gc.minor_collection()
        p1 = check_alive(0)
        self.gc.collect()
        py.test.raises(RuntimeError, "r1.ob_refcnt")    # dead
        py.test.raises(RuntimeError, "p1.x")            # dead
        self.gc.check_no_more_rawrefcount_state()
        assert self.dealloc == []

    def test_rawrefcount_objects_collection_survives_from_obj(self):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_direct=True))
        check_alive(0)
        self.stackroots.append(p1)
        self.gc.minor_collection()
        check_alive(0)
        self.gc.collect()
        check_alive(0)
        p1 = self.stackroots.pop()
        self.gc.minor_collection()
        check_alive(0)
        assert p1.x == 42
        self.gc.collect()
        py.test.raises(RuntimeError, "r1.ob_refcnt")    # dead
        py.test.raises(RuntimeError, "p1.x")            # dead
        self.gc.check_no_more_rawrefcount_state()
        assert self.dealloc == []

    def test_pypy_nondirect_survives_from_raw(self):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_direct=False))
        check_alive(0)
        r1.ob_refcnt += 1
        self.gc.minor_collection()
        check_alive(+1)
        self.gc.collect()
        check_alive(+1)
        r1.ob_refcnt -= 1
        self.gc.minor_collection()
        p1 = check_alive(0)
        assert self.dealloc == []
        self.gc.collect()
        py.test.raises(RuntimeError, "p1.x")            # dead
        assert r1.ob_refcnt == 0
        assert r1.ob_pypy_link == 0
        assert self.dealloc == [r1addr]
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')

    def test_pypy_nondirect_survives_from_obj(self):
        p1, p1ref, r1, r1addr, check_alive = (
            self._rawrefcount_pair(42, is_direct=False))
        check_alive(0)
        self.stackroots.append(p1)
        self.gc.minor_collection()
        check_alive(0)
        self.gc.collect()
        check_alive(0)
        p1 = self.stackroots.pop()
        self.gc.minor_collection()
        check_alive(0)
        assert p1.x == 42
        assert self.dealloc == []
        self.gc.collect()
        py.test.raises(RuntimeError, "p1.x")            # dead
        assert r1.ob_refcnt == 0
        assert r1.ob_pypy_link == 0
        assert self.dealloc == [r1addr]
        self.gc.check_no_more_rawrefcount_state()
        lltype.free(r1, flavor='raw')
