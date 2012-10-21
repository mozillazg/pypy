

_LONGLONGARRAY = lltype.GcArray(lltype.SignedLongLong)

JITFRAME = lltype.GcStruct(
    'JITFRAME',

    # Once the execute_token() returns, the field 'jf_descr' stores the
    # descr of the last executed operation (either a GUARD, or FINISH).
    ('jf_descr', llmemory.GCREF),

    # For the front-end: a GCREF for the savedata
    ('jf_savedata', llmemory.GCREF),

    # XXX
    ('jf_nongcvalues', lltype.Ptr(_LONGLONGARRAY)),
    ('jf_gcvalues', lltype.Array(llmemory.GCREF)))
JITFRAMEPTR = lltype.Ptr(JITFRAME)
