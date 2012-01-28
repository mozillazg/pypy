from pypy.rpython.memory.gctransform.shadowstack import ShadowStackRootWalker
from pypy.rpython.memory.gctransform.shadowstack import sizeofaddr
from pypy.rpython.lltypesystem import lltype, llmemory, rffi


class MockGC:
    def points_to_valid_gc_object(self, addr):
        n = rffi.cast(lltype.Signed, addr.address[0])
        if n > 0x1000:
            return True
        if n == 0:
            return False
        assert 0, "oups, bogus address: 0x%x" % n

class MockGCData:
    gc = MockGC()

class MockGcTransformer:
    gcdata = MockGCData()
    translator = None
    root_stack_depth = None


def test_default_walk_stack_root():
    for (minor, already_traced) in [(False, False),
                                    (False, True),
                                    (True, False),
                                    (True, True)]:
        root_stack_size = sizeofaddr * 5
        a = llmemory.raw_malloc(root_stack_size)
        a.address[0] = llmemory.NULL
        a.address[1] = rffi.cast(llmemory.Address, 0x1234)
        if already_traced:
            marker = ShadowStackRootWalker.MARKER_TRACED
        else:
            marker = ShadowStackRootWalker.MARKER_NOT_TRACED
        a.address[2] = rffi.cast(llmemory.Address, marker)
        a.address[3] = rffi.cast(llmemory.Address, 0x5678)
        a.address[4] = llmemory.NULL
        walker = ShadowStackRootWalker(MockGcTransformer())
        seen = []
        def callback(gc, addr):
            assert gc == walker.gc
            seen.append(rffi.cast(lltype.Signed, addr.address[0]))
        aend = a + 5 * sizeofaddr
        walker.rootstackhook(callback, a, aend, is_minor=minor)
        marker = rffi.cast(lltype.Signed, a.address[2])
        assert marker == ShadowStackRootWalker.MARKER_TRACED
        if minor and already_traced:
            assert seen == [0x5678]
        else:
            assert seen == [0x5678, 0x1234]
        llmemory.raw_free(a)

