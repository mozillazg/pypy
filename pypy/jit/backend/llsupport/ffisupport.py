from pypy.jit.metainterp import history
from pypy.jit.backend.llsupport.descr import DynamicIntCallDescr, NonGcPtrCallDescr,\
    FloatCallDescr, VoidCallDescr

def get_call_descr_dynamic(ffi_args, ffi_result, extrainfo=None):
    """Get a call descr: the types of result and args are represented by
    rlib.libffi.ffi_type_*"""
    try:
        reskind = get_ffi_type_kind(ffi_result)
        argkinds = [get_ffi_type_kind(arg) for arg in ffi_args]
    except KeyError:
        return None # ??
    arg_classes = ''.join(argkinds)
    if reskind == history.INT:
        return DynamicIntCallDescr(arg_classes, ffi_result.c_size, extrainfo)
    elif reskind == history.REF:
        return  NonGcPtrCallDescr(arg_classes, extrainfo)
    elif reskind == history.FLOAT:
        return FloatCallDescr(arg_classes, extrainfo)
    elif reskind == history.VOID:
        return VoidCallDescr(arg_classes, extrainfo)
    assert False


# XXX: maybe we can turn this into a dictionary, but we need to do it at
# runtime as libffi.ffi_type_* are pointers
def get_ffi_type_kind(ffi_type):
    from pypy.rlib import libffi
    if ffi_type is libffi.ffi_type_void:
        return history.VOID
    elif ffi_type is libffi.ffi_type_pointer:
        return history.REF
    elif ffi_type is libffi.ffi_type_double:
        return history.FLOAT
    elif ffi_type is libffi.ffi_type_uchar:
        return history.INT
    elif ffi_type is libffi.ffi_type_uint8:
        return history.INT
    elif ffi_type is libffi.ffi_type_schar:
        return history.INT
    elif ffi_type is libffi.ffi_type_sint8:
        return history.INT
    elif ffi_type is libffi.ffi_type_uint16:
        return history.INT
    elif ffi_type is libffi.ffi_type_ushort:
        return history.INT
    elif ffi_type is libffi.ffi_type_sint16:
        return history.INT
    elif ffi_type is libffi.ffi_type_sshort:
        return history.INT
    elif ffi_type is libffi.ffi_type_uint:
        return history.INT
    elif ffi_type is libffi.ffi_type_uint32:
        return history.INT
    elif ffi_type is libffi.ffi_type_sint:
        return history.INT
    elif ffi_type is libffi.ffi_type_sint32:
        return history.INT
    ## elif ffi_type is libffi.ffi_type_uint64:
    ##     return history.INT
    ## elif ffi_type is libffi.ffi_type_sint64:
    ##     return history.INT
    raise KeyError
