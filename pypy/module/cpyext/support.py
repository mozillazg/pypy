from rpython.rtyper.lltypesystem import lltype, rffi

memcpy_fn = rffi.llexternal('memcpy', [rffi.CCHARP, rffi.CCHARP,
                                       rffi.SIZE_T], lltype.Void,
                            sandboxsafe=True)
memset_fn = rffi.llexternal('memset', [rffi.CCHARP, rffi.INT,
                                       rffi.SIZE_T], lltype.Void,
                            sandboxsafe=True)
