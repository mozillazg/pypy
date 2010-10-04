from pypy.jit.metainterp import history
from pypy.jit.backend.llsupport.descr import DynamicIntCallDescr, NonGcPtrCallDescr,\
    FloatCallDescr, VoidCallDescr

def get_call_descr_dynamic(ffi_args, ffi_result, extrainfo=None):
    """Get a call descr: the types of result and args are represented by
    rlib.libffi.types.*"""
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
# runtime as libffi.types.* pointers
def get_ffi_type_kind(ffi_type):
    from pypy.rlib.libffi import types
    if ffi_type is types.void:
        return history.VOID
    elif ffi_type is types.pointer:
        return history.REF
    elif ffi_type is types.double:
        return history.FLOAT
    elif ffi_type is types.uchar:
        return history.INT
    elif ffi_type is types.uint8:
        return history.INT
    elif ffi_type is types.schar:
        return history.INT
    elif ffi_type is types.sint8:
        return history.INT
    elif ffi_type is types.uint16:
        return history.INT
    elif ffi_type is types.ushort:
        return history.INT
    elif ffi_type is types.sint16:
        return history.INT
    elif ffi_type is types.sshort:
        return history.INT
    elif ffi_type is types.uint:
        return history.INT
    elif ffi_type is types.uint32:
        return history.INT
    elif ffi_type is types.sint:
        return history.INT
    elif ffi_type is types.sint32:
        return history.INT
    ## elif ffi_type is types.uint64:
    ##     return history.INT
    ## elif ffi_type is types.sint64:
    ##     return history.INT
    raise KeyError
