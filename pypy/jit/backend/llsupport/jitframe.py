

_LONGLONGARRAY = lltype.GcArray(lltype.SignedLongLong)

JITFRAME = lltype.GcStruct('JITFRAME',
               ('jf_descr', llmemory.GCREF),
               ('jf_excvalue', llmemory.GCREF),
               ('jf_nongcvalues', lltype.Ptr(_LONGLONGARRAY)),
               ('jf_gcvalues', lltype.Array(llmemory.GCREF)))
JITFRAMEPTR = lltype.Ptr(JITFRAME)
