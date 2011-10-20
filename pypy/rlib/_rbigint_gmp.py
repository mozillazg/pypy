from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo

eci = ExternalCompilationInfo(includes=["gmp.h"],
                              libraries=["gmp"])

mpz_t = rffi.COpaque("mpz_t", ptr_typedef="mpz_ptr", compilation_info=eci)
mpz_ptr = lltype.Ptr(mpz_t)

def external(name, args, result=lltype.Void):
    name = "__g" + name    # temporary hack?
    return rffi.llexternal(name, args, result, compilation_info=eci)

mpz_init        = external("mpz_init", [mpz_ptr])
mpz_init_set_si = external("mpz_init_set_si", [mpz_ptr, rffi.LONG])
mpz_get_si      = external("mpz_get_si", [mpz_ptr], rffi.LONG)
mpz_add         = external("mpz_add", [mpz_ptr, mpz_ptr, mpz_ptr])
mpz_sub         = external("mpz_sub", [mpz_ptr, mpz_ptr, mpz_ptr])
mpz_mul         = external("mpz_mul", [mpz_ptr, mpz_ptr, mpz_ptr])

# ____________________________________________________________

class _adtmeths:

    @lltype.typeMethod
    def fromint(RBIGINT, value):
        r = lltype.malloc(RBIGINT)
        mpz_init_set_si(r.mpz, value)
        return r

    def tolong(r):
        return mpz_get_si(r.mpz)

    def add(r1, r2):
        r = lltype.malloc(RBIGINT)
        mpz_init(r.mpz)
        mpz_add(r.mpz, r1.mpz, r2.mpz)
        return r

    def sub(r1, r2):
        r = lltype.malloc(RBIGINT)
        mpz_init(r.mpz)
        mpz_sub(r.mpz, r1.mpz, r2.mpz)
        return r

    def mul(r1, r2):
        r = lltype.malloc(RBIGINT)
        mpz_init(r.mpz)
        mpz_mul(r.mpz, r1.mpz, r2.mpz)
        return r

_adtmeths = dict([(key, value) for (key, value) in _adtmeths.__dict__.items()
                               if not key.startswith('_')])

RBIGINT = lltype.GcStruct("RBIGINT_GMP",
                          ('mpz', mpz_t),
                          adtmeths = _adtmeths)
# XXX call mpz_clear() in a lightweight finalizer
