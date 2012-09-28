from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem.rvirtualizable2 import JITFRAMEPTR


_LONGLONGARRAY = lltype.GcArray(lltype.SignedLongLong)

JITFRAME = lltype.GcStruct('JITFRAME',
               ('jf_descr', llmemory.GCREF),
               ('jf_excvalue', llmemory.GCREF),
               ('jf_nongcvalues', lltype.Ptr(_LONGLONGARRAY)),
               ('jf_gcvalues', lltype.Array(llmemory.GCREF)))
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
