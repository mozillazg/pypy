
""" Base operations implementations
"""

from pypy.lang.js.jsobj import W_String, W_IntNumber, W_FloatNumber
from pypy.rlib.rarithmetic import r_uint, intmask, INFINITY, NAN, ovfcheck,\
     isnan, isinf

def plus(ctx, nleft, nright):
    if isinstance(nleft, W_String) or isinstance(nright, W_String):
        sleft = nleft.ToString(ctx)
        sright = nright.ToString(ctx)
        return W_String(sleft + sright)
    # hot path
    if isinstance(nleft, W_IntNumber) and isinstance(nright, W_IntNumber):
        ileft = nleft.ToInt32()
        iright = nright.ToInt32()
        try:
            return W_IntNumber(ovfcheck(ileft + iright))
        except OverflowError:
            return W_FloatNumber(float(ileft) + float(iright))
    else:
        fleft = nleft.ToNumber()
        fright = nright.ToNumber()
        return W_FloatNumber(fleft + fright)

def sub(ctx, nleft, nright):
    if isinstance(nleft, W_IntNumber) and isinstance(nright, W_IntNumber):
        ileft = nleft.ToInt32()
        iright = nright.ToInt32()
        try:
            return W_IntNumber(ovfcheck(ileft - iright))
        except OverflowError:
            return W_FloatNumber(float(ileft) - float(iright))
    fleft = nleft.ToNumber()
    fright = nright.ToNumber()
    return W_FloatNumber(fleft - fright)
