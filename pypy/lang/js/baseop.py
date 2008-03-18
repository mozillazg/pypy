
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
        ileft = nleft.intval
        iright = nright.intval
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

def mult(ctx, nleft, nright):
    if isinstance(nleft, W_IntNumber) and isinstance(nright, W_IntNumber):
        ileft = nleft.ToInt32()
        iright = nright.ToInt32()
        try:
            return W_IntNumber(ovfcheck(ileft * iright))
        except OverflowError:
            return W_FloatNumber(float(ileft) * float(iright))
    fleft = nleft.ToNumber()
    fright = nright.ToNumber()
    return W_FloatNumber(fleft * fright)

def mod(ctx, nleft, nright): # XXX this one is really not following spec
    ileft = nleft.ToInt32()
    iright = nright.ToInt32()
    return W_IntNumber(ileft % iright)

def division(ctx, nleft, nright):
    fleft = nleft.ToNumber()
    fright = nright.ToNumber()
    if fright == 0:
        if fleft < 0:
            val = -INFINITY
        elif fleft == 0:
            val = NAN
        else:
            val = INFINITY
    else:
        val = fleft / fright
    return W_FloatNumber(val)

def compare(ctx, x, y):
    if isinstance(x, W_IntNumber) and isinstance(y, W_IntNumber):
        return x.intval > y.intval
    if isinstance(x, W_FloatNumber) and isinstance(y, W_FloatNumber):
        if isnan(x.floatval) or isnan(y.floatval):
            return -1
        return x.floatval > y.floatval
    s1 = x.ToPrimitive(ctx, 'Number')
    s2 = y.ToPrimitive(ctx, 'Number')
    if not (isinstance(s1, W_String) and isinstance(s2, W_String)):
        s4 = s1.ToNumber()
        s5 = s2.ToNumber()
        if isnan(s4) or isnan(s5):
            return False
        return s4 > s5
    else:
        s4 = s1.ToString(ctx)
        s5 = s2.ToString(ctx)
        return s4 > s5

def compare_e(ctx, x, y):
    if isinstance(x, W_IntNumber) and isinstance(y, W_IntNumber):
        return x.intval >= y.intval
    if isinstance(x, W_FloatNumber) and isinstance(y, W_FloatNumber):
        if isnan(x.floatval) or isnan(y.floatval):
            return -1
        return x.floatval >= y.floatval
    s1 = x.ToPrimitive(ctx, 'Number')
    s2 = y.ToPrimitive(ctx, 'Number')
    if not (isinstance(s1, W_String) and isinstance(s2, W_String)):
        s4 = s1.ToNumber()
        s5 = s2.ToNumber()
        if isnan(s4) or isnan(s5):
            return False
        return s4 >= s5
    else:
        s4 = s1.ToString(ctx)
        s5 = s2.ToString(ctx)
        return s4 >= s5

def AbstractEC(ctx, x, y):
    """
    Implements the Abstract Equality Comparison x == y
    trying to be fully to the spec
    """
    if isinstance(x, W_IntNumber) and isinstance(y, W_IntNumber):
        return x.intval == y.intval
    if isinstance(x, W_FloatNumber) and isinstance(y, W_FloatNumber):
        if isnan(x.floatval) or isnan(y.floatval):
            return False
        return x.floatval == y.floatval
    type1 = x.type()
    type2 = y.type()
    if type1 == type2:
        if type1 == "undefined" or type1 == "null":
            return True
        if type1 == "number":
            n1 = x.ToNumber()
            n2 = y.ToNumber()
            if isnan(n1) or isnan(n2):
                return False
            if n1 == n2:
                return True
            return False
        elif type1 == "string":
            return x.ToString(ctx) == y.ToString(ctx)
        elif type1 == "boolean":
            return x.ToBoolean() == x.ToBoolean()
        return x == y
    else:
        #step 14
        if (type1 == "undefined" and type2 == "null") or \
           (type1 == "null" and type2 == "undefined"):
            return True
        if type1 == "number" and type2 == "string":
            return AbstractEC(ctx, x, W_FloatNumber(y.ToNumber()))
        if type1 == "string" and type2 == "number":
            return AbstractEC(ctx, W_FloatNumber(x.ToNumber()), y)
        if type1 == "boolean":
            return AbstractEC(ctx, W_FloatNumber(x.ToNumber()), y)
        if type2 == "boolean":
            return AbstractEC(ctx, x, W_FloatNumber(y.ToNumber()))
        if (type1 == "string" or type1 == "number") and \
            type2 == "object":
            return AbstractEC(ctx, x, y.ToPrimitive(ctx))
        if (type2 == "string" or type2 == "number") and \
            type1 == "object":
            return AbstractEC(ctx, x.ToPrimitive(ctx), y)
        return False
            
        
    objtype = x.GetValue().type()
    if objtype == y.GetValue().type():
        if objtype == "undefined" or objtype == "null":
            return True
        
    if isinstance(x, W_String) and isinstance(y, W_String):
        r = x.ToString(ctx) == y.ToString(ctx)
    else:
        r = x.ToNumber() == y.ToNumber()
    return r

def StrictEC(ctx, x, y):
    """
    Implements the Strict Equality Comparison x === y
    trying to be fully to the spec
    """
    type1 = x.type()
    type2 = y.type()
    if type1 != type2:
        return False
    if type1 == "undefined" or type1 == "null":
        return True
    if type1 == "number":
        n1 = x.ToNumber()
        n2 = y.ToNumber()
        if isnan(n1) or isnan(n2):
            return False
        if n1 == n2:
            return True
        return False
    if type1 == "string":
        return x.ToString(ctx) == y.ToString(ctx)
    if type1 == "boolean":
        return x.ToBoolean() == x.ToBoolean()
    return x == y
