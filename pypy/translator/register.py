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
    post_include_bits=['register void* pypy_reg asm("r15");'],
    )

_test_eci = eci.merge(ExternalCompilationInfo(
    post_include_bits=["""
            void f(void) {
                pypy_reg = &f;
            }
    """]))

try:
    rffi_platform.verify_eci(_test_eci)
    var_name_in_c = 'pypy_reg'
    register_number = 15      # r15
except rffi_platform.CompilationError:
    eci = None
    var_name_in_c = None
    register_number = None
