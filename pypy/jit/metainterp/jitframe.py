from pypy.rpython.lltypesystem import lltype, llmemory


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
#      as fetched with the 'FORCE_TOKEN' resoperation.
#
TOKEN_NONE = lltype.nullptr(llmemory.GCREF.TO)

_JITFRAME_TRACING = lltype.GcStruct('JITFRAME_TRACING')
TOKEN_TRACING_RESCALL = lltype.cast_opaque_ptr(
    llmemory.GCREF, lltype.malloc(_JITFRAME_TRACING, immortal=True))
