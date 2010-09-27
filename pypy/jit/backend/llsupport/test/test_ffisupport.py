from pypy.rlib import libffi
from pypy.jit.backend.llsupport.ffisupport import get_call_descr_dynamic, \
    VoidCallDescr, DynamicIntCallDescr
    
def test_call_descr_dynamic():

    args = [libffi.ffi_type_sint, libffi.ffi_type_double, libffi.ffi_type_pointer]
    descr = get_call_descr_dynamic(args, libffi.ffi_type_void)
    assert isinstance(descr, VoidCallDescr)
    assert descr.arg_classes == 'ifr'

    descr = get_call_descr_dynamic([], libffi.ffi_type_sint8)
    assert isinstance(descr, DynamicIntCallDescr)
    assert descr.get_result_size(False) == 1

    descr = get_call_descr_dynamic([], libffi.ffi_type_float)
    assert descr is None # single floats are not supported so far
    
