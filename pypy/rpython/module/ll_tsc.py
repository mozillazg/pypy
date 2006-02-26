from pypy.rpython.rarithmetic import r_longlong

def ll_tsc_read():
    return r_longlong(0)
ll_tsc_read.suggested_primitive = True

def ll_tsc_read_diff():
    return 0
ll_tsc_read_diff.suggested_primitive = True

def ll_tsc_reset_diff():
    pass
ll_tsc_reset_diff.suggested_primitive = True
