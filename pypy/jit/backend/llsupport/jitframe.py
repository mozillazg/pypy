from pypy.rpython.lltypesystem import lltype, llmemory


JITFRAME = lltype.GcStruct(
    'JITFRAME',

    # Once the execute_token() returns, the field 'jf_descr' stores the
    # descr of the last executed operation (either a GUARD, or FINISH).
    # This field is also set immediately before doing CALL_MAY_FORCE.
    ('jf_descr', llmemory.GCREF),

    # For the front-end: a GCREF for the savedata
    ('jf_savedata', llmemory.GCREF),

    # All values are stored in the following array.
    ('jf_values', lltype.Array(llmemory.Address)))

JITFRAMEPTR = lltype.Ptr(JITFRAME)
