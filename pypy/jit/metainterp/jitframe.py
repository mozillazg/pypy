from pypy.rpython.lltypesystem import lltype, llmemory, rffi


GCINDEXLIST = lltype.GcArray(rffi.UINT)

JITFRAME = lltype.GcStruct('JITFRAME',
                           ('gcindexlist', lltype.Ptr(GCINDEXLIST)),
                           ('items', lltype.Array(llmemory.Address)))
JITFRAMEPTR = lltype.Ptr(JITFRAME)

# ____________________________________________________________

FRAME_ITERATOR = lltype.GcStruct('FRAME_ITERATOR',
                                 ('remaining_indices', lltype.Signed))
frame_iterator = lltype.malloc(FRAME_ITERATOR, immortal=True)

GCINDEXLIST_OFS = llmemory.offsetof(JITFRAME, 'gcindexlist')
ITEMS_BASE_OFS = (llmemory.offsetof(JITFRAME, 'items') +
                  llmemory.itemoffsetof(JITFRAME.items))
SIZE_OF_ADDR = llmemory.sizeof(llmemory.Address)

def customtrace(obj, prev):
    gcindexlist = llmemory.cast_adr_to_ptr(obj, JITFRAMEPTR).gcindexlist
    if not prev:
        # return first the address of the 'gcindexlist' field
        frame_iterator.remaining_indices = len(gcindexlist)
        return obj + GCINDEXLIST_OFS
    elif frame_iterator.remaining_indices > 0:
        # return next the addresses of '.items[n]', for n in gcindexlist
        frame_iterator.remaining_indices -= 1
        n = gcindexlist[frame_iterator.remaining_indices]
        n = lltype.cast_primitive(lltype.Signed, n)
        return obj + ITEMS_BASE_OFS + n * SIZE_OF_ADDR
    else:
        return llmemory.NULL

CUSTOMTRACEFUNC = lltype.FuncType([llmemory.Address, llmemory.Address],
                                  llmemory.Address)
customtraceptr = llhelper(lltype.Ptr(CUSTOMTRACEFUNC), customtrace)
lltype.attachRuntimeTypeInfo(SHADOWSTACKREF, customtraceptr=customtraceptr)
