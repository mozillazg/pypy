from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.tool import rffi_platform

# On platforms with enough hardware registers and with gcc, we can
# (ab)use gcc to globally assign a register to a single global void*
# variable.  We use it with a double meaning:
#
# - when it is NULL upon return from a function, it means that an
#   exception occurred.  It allows the caller to quickly check for
#   exceptions.
#
# - in other cases, with --gcrootfinder=shadowstack, it points to
#   the top of the shadow stack.


# For now, only for x86-64.  Tries to use the register r15.
eci = ExternalCompilationInfo(
    post_include_bits=[
        'register void *pypy_r15 asm("r15");\n'
        '#define PYPY_GET_SPECIAL_REG() pypy_r15\n'
        '#define PYPY_SPECIAL_REG_NONNULL() (pypy_r15 != NULL)\n'
        '#define PYPY_SET_SPECIAL_REG(x) (pypy_r15 = x)\n'
        ],
    )

_test_eci = eci.merge(ExternalCompilationInfo(
    post_include_bits=["""
            void f(void) {
                pypy_r15 = &f;
            }
    """]))

try:
    rffi_platform.verify_eci(_test_eci)
    register_number = 15      # r15
except rffi_platform.CompilationError:
    eci = None
    register_number = None
else:

    from pypy.rpython.lltypesystem import lltype, llmemory, rffi

    # use addr=load_from_reg() and store_into_reg(addr) to load and store
    # an Address out of the special register.  When running on top of Python,
    # the behavior is emulated.

    _value_reg = None

    def _pypy_get_special_reg():
        assert _value_reg is not None
        return _value_reg

    def _pypy_special_reg_nonnull():
        assert _value_reg is not None
        return bool(_value_reg)

    def _pypy_set_special_reg(addr):
        global _value_reg
        _value_reg = addr

    load_from_reg = rffi.llexternal('PYPY_GET_SPECIAL_REG', [],
                                    llmemory.Address,
                                    _callable=_pypy_get_special_reg,
                                    compilation_info=eci,
                                    _nowrapper=True)

    reg_is_nonnull = rffi.llexternal('PYPY_SPECIAL_REG_NONNULL', [],
                                     lltype.Bool,
                                     _callable=_pypy_special_reg_nonnull,
                                     compilation_info=eci,
                                     _nowrapper=True)

    store_into_reg = rffi.llexternal('PYPY_SET_SPECIAL_REG',
                                     [llmemory.Address],
                                     lltype.Void,
                                     _callable=_pypy_set_special_reg,
                                     compilation_info=eci,
                                     _nowrapper=True)

    # xxx temporary
    nonnull = llmemory.cast_int_to_adr(-1)
