from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem.rvirtualizable2 import JITFRAMEPTR


GCINDEXLIST = lltype.GcArray(rffi.USHORT)

JITFRAME = lltype.GcStruct('JITFRAME',
                           ('gcindexlist', lltype.Ptr(GCINDEXLIST)),
                           ('items', lltype.Array(llmemory.Address)),
                           rtti=True)
JITFRAMEPTR.TO.become(JITFRAME)

# Constants used for the 'jit_frame' field of virtualizables/virtualrefs:
#
#   1. TOKEN_NONE means not in the JIT at all, except as described below.
#
#   2. TOKEN_NONE too when tracing is in progress; except:
#
#   3. the special value TOKEN_TRACING_RESCALL during tracing when we do a
#      residual call, calling random unknown other parts of the interpreter;
#      it is reset to TOKEN_NONE as soon as something occurs to the
#      virtualizable.
#
#   4. when running the machine code with a virtualizable, it is set
#      to the actual CPU frame allocated by the generated assembler,
#      as fetched with the 'JIT_FRAME' resoperation.
#
TOKEN_NONE            = lltype.nullptr(JITFRAME)
TOKEN_TRACING_RESCALL = lltype.malloc(JITFRAME, 0, immortal=True, zero=True)

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
lltype.attachRuntimeTypeInfo(JITFRAME, customtraceptr=customtraceptr)
