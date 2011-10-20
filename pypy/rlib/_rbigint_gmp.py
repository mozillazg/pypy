from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.lltypesystem.lltype import typeMethod
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib import jit
from pypy.rlib.objectmodel import specialize

eci = ExternalCompilationInfo(includes=["gmp.h"],
                              libraries=["gmp"])

mpz_t = rffi.COpaque("mpz_t", ptr_typedef="mpz_ptr", compilation_info=eci)
mpz_ptr = lltype.Ptr(mpz_t)

def external(name, args, result=lltype.Void):
    if name.startswith('mp'):
        name = "__g" + name    # temporary hack?
    return rffi.llexternal(name, args, result, compilation_info=eci)

mpz_init        = external("mpz_init", [mpz_ptr])
mpz_init_set_si = external("mpz_init_set_si", [mpz_ptr, rffi.LONG])
mpz_init_set_str= external("mpz_init_set_str", [mpz_ptr, rffi.CCHARP,rffi.INT])
mpz_get_si      = external("mpz_get_si", [mpz_ptr], rffi.LONG)
mpz_get_ui      = external("mpz_get_ui", [mpz_ptr], rffi.ULONG)
mpz_get_str     = external("mpz_get_str", [rffi.CCHARP, rffi.INT, mpz_ptr],
                           rffi.CCHARP)
mpz_add         = external("mpz_add", [mpz_ptr, mpz_ptr, mpz_ptr])
mpz_sub         = external("mpz_sub", [mpz_ptr, mpz_ptr, mpz_ptr])
mpz_mul         = external("mpz_mul", [mpz_ptr, mpz_ptr, mpz_ptr])
mpz_fdiv_q      = external("mpz_fdiv_q", [mpz_ptr, mpz_ptr, mpz_ptr])
mpz_fdiv_r      = external("mpz_fdiv_r", [mpz_ptr, mpz_ptr, mpz_ptr])
mpz_pow_ui      = external("mpz_pow_ui", [mpz_ptr, mpz_ptr, rffi.ULONG])

mpz_fits_ulong_p = external("mpz_fits_ulong_p", [mpz_ptr], rffi.INT)

_free           = external("free", [rffi.CCHARP])

# ____________________________________________________________


def _fromint(value):
    r = lltype.malloc(RBIGINT)
    mpz_init_set_si(r.mpz, value)
    return r

def _str_base_10(r):
    p = mpz_get_str(lltype.nullptr(rffi.CCHARP.TO), 10, r.mpz)
    result = rffi.charp2str(p)
    _free(p)
    return result


class _adtmeths:

    @typeMethod
    @jit.elidable
    def fromint(RBIGINT, value):
        return _fromint(value)

    @typeMethod
    def frombool(RBIGINT, b):
        return _fromint(int(b))    # maybe do some caching?

    @typeMethod
    def fromlong(RBIGINT, l):
        "NOT_RPYTHON"
        r = lltype.malloc(RBIGINT)
        mpz_init_set_str(r.mpz, str(l), 10)
        return r

    str = _str_base_10

    def tolong(r):
        "NOT_RPYTHON"
        return int(_str_base_10(r))

    def _binary(opname):
        mpz_op = globals()['mpz_' + opname]
        def operation(r1, r2):
            r = lltype.malloc(RBIGINT)
            mpz_init(r.mpz)
            mpz_op(r.mpz, r1.mpz, r2.mpz)
            return r
        operation.__name__ = opname
        return operation

    add = _binary('add')
    sub = _binary('sub')
    mul = _binary('mul')
    div = _binary('fdiv_q')
    floordiv = div
    mod = _binary('fdiv_r')

    def truediv(r1, r2):
        import py; py.test.skip("XXX")

    @specialize.argtype(2)
    def pow(a, b, c=None):
        if c is None:
            fits = rffi.cast(lltype.Signed, mpz_fits_ulong_p(b.mpz))
            assert fits, "XXX"
            b_ulong = mpz_get_ui(b.mpz)
            r = lltype.malloc(RBIGINT)
            mpz_init(r.mpz)
            mpz_pow_ui(r.mpz, a.mpz, b_ulong)
            return r
        else:
            yyy

_adtmeths = dict([(key, value) for (key, value) in _adtmeths.__dict__.items()
                               if not key.startswith('_')])

# ____________________________________________________________

RBIGINT = lltype.GcStruct("RBIGINT_GMP",
                          ('mpz', mpz_t),
                          adtmeths = _adtmeths)
# XXX call mpz_clear() in a lightweight finalizer
