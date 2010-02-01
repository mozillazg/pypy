from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.rposix import get_errno

class OProfileError(Exception):
    def __init__(self, errno, where):
        self.errno = errno
        self.where = where


eci = ExternalCompilationInfo(includes=['stdint.h', 'opagent.h'],
                              library_dirs=['/usr/local/lib/oprofile/'],
                              libraries=['bfd', 'opagent'])
try:
    rffi_platform.verify_eci(eci)
except rffi_platform.CompilationError:
    OPROFILE_AVAILABLE = False
else:
    OPROFILE_AVAILABLE = True
    AGENT = rffi.VOIDP
    uint64_t = rffi.ULONGLONG
    op_open_agent = rffi.llexternal(
        "op_open_agent",
        [],
        AGENT,
        compilation_info=eci)
    op_close_agent = rffi.llexternal(
        "op_close_agent",
        [AGENT],
        rffi.INT,
        compilation_info=eci)
    # arguments are:
    # agent, symbol_name, address in memory, address in memory again, size
    op_write_native_code = rffi.llexternal(
        "op_write_native_code",
        [AGENT, rffi.CCHARP, uint64_t, rffi.VOIDP, rffi.UINT],
        rffi.INT,
        compilation_info=eci)

def startup(cpu):
    if not OPROFILE_AVAILABLE:
        return
    agent = op_open_agent()
    if not agent:
        cpu._oprofile_agent = rffi.cast(rffi.VOIDP, 0)
        raise OProfileError(get_errno(), "startup")
    cpu._oprofile_agent = agent

def shutdown(cpu):
    if not OPROFILE_AVAILABLE:
        return
    if cpu._oprofile_agent:
        success = op_close_agent(cpu._oprofile_agent)
        if success != 0:
            raise OProfileError(get_errno(), "shutdown")

def native_code_written(cpu, name, address, size):
    assert size > 0
    if not OPROFILE_AVAILABLE:
        return
    uaddress = rffi.cast(rffi.ULONG, address)
    success = op_write_native_code(cpu._oprofile_agent, name, uaddress, rffi.cast(rffi.VOIDP, 0), size)
    if success != 0:
        raise OProfileError(get_errno(), "write")
