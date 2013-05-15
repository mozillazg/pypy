from pypy.interpreter import typedef
from pypy.interpreter.buffer import Buffer
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault,\
     interpindirect2app
from pypy.objspace.std import newformat
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.multimethod import FailedToImplementArgs
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.objspace.std.strutil import (string_to_int, string_to_bigint,
                                       ParseStringError,
                                       ParseStringOverflowError)
from rpython.rlib import jit
from rpython.rlib.objectmodel import instantiate
from rpython.rlib.rarithmetic import ovfcheck, LONG_BIT, r_uint, is_valid_int
from rpython.rlib.rbigint import rbigint

"""
In order to have the same behavior running
on CPython, and after RPython translation we use ovfcheck
from rarithmetic to explicitly check for overflows,
something CPython does not do anymore.
"""

class W_AbstractIntObject(W_Object):
    __slots__ = ()

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractIntObject):
            return False
        if self.user_overridden_class or w_other.user_overridden_class:
            return self is w_other
        return space.int_w(self) == space.int_w(w_other)

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        from pypy.objspace.std.model import IDTAG_INT as tag
        b = space.bigint_w(self)
        b = b.lshift(3).or_(rbigint.fromint(tag))
        return space.newlong_from_rbigint(b)

    def int(self, space):
        raise NotImplementedError

class W_IntObject(W_AbstractIntObject):
    __slots__ = 'intval'
    _immutable_fields_ = ['intval']

    def __init__(w_self, intval):
        assert is_valid_int(intval)
        w_self.intval = intval

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%d)" % (w_self.__class__.__name__, w_self.intval)

    def unwrap(w_self, space):
        return int(w_self.intval)
    int_w = unwrap

    def uint_w(w_self, space):
        intval = w_self.intval
        if intval < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("cannot convert negative integer to unsigned"))
        else:
            return r_uint(intval)

    def bigint_w(w_self, space):
        return rbigint.fromint(w_self.intval)

    def float_w(self, space):
        return float(self.intval)

    def int(self, space):
        if (type(self) is not W_IntObject and
            space.is_overloaded(self, space.w_int, '__int__')):
            return W_Object.int(self, space)
        if space.is_w(space.type(self), space.w_int):
            return self
        a = self.intval
        return wrapint(space, a)

# ____________________________________________________________

def descr_conjugate(space, w_int):
    "Returns self, the complex conjugate of any int."
    return space.int(w_int)

def descr_bit_length(space, w_int):
    """int.bit_length() -> int

    Number of bits necessary to represent self in binary.
    >>> bin(37)
    '0b100101'
    >>> (37).bit_length()
    6
    """
    val = space.int_w(w_int)
    if val < 0:
        val = -val
    bits = 0
    while val:
        bits += 1
        val >>= 1
    return space.wrap(bits)


def wrapint(space, x):
    if space.config.objspace.std.withprebuiltint:
        from pypy.objspace.std.intobject import W_IntObject
        lower = space.config.objspace.std.prebuiltintfrom
        upper =  space.config.objspace.std.prebuiltintto
        # use r_uint to perform a single comparison (this whole function
        # is getting inlined into every caller so keeping the branching
        # to a minimum is a good idea)
        index = r_uint(x - lower)
        if index >= r_uint(upper - lower):
            w_res = instantiate(W_IntObject)
        else:
            w_res = W_IntObject.PREBUILT[index]
        # obscure hack to help the CPU cache: we store 'x' even into
        # a prebuilt integer's intval.  This makes sure that the intval
        # field is present in the cache in the common case where it is
        # quickly reused.  (we could use a prefetch hint if we had that)
        w_res.intval = x
        return w_res
    else:
        from pypy.objspace.std.intobject import W_IntObject
        return W_IntObject(x)

# ____________________________________________________________

def string_to_int_or_long(space, string, base=10):
    w_longval = None
    value = 0
    try:
        value = string_to_int(string, base)
    except ParseStringError, e:
        raise OperationError(space.w_ValueError,
                             space.wrap(e.msg))
    except ParseStringOverflowError, e:
        w_longval = retry_to_w_long(space, e.parser)
    return value, w_longval

def retry_to_w_long(space, parser, base=0):
    parser.rewind()
    try:
        bigint = string_to_bigint(None, base=base, parser=parser)
    except ParseStringError, e:
        raise OperationError(space.w_ValueError,
                             space.wrap(e.msg))
    from pypy.objspace.std.longobject import newlong
    return newlong(space, bigint)

@unwrap_spec(w_x = WrappedDefault(0))
def descr__new__(space, w_inttype, w_x, w_base=None):
    from pypy.objspace.std.intobject import W_IntObject
    w_longval = None
    w_value = w_x     # 'x' is the keyword argument name in CPython
    value = 0
    if w_base is None:
        ok = False
        # check for easy cases
        if type(w_value) is W_IntObject:
            value = w_value.intval
            ok = True
        elif space.isinstance_w(w_value, space.w_str):
            value, w_longval = string_to_int_or_long(space, space.str_w(w_value))
            ok = True
        elif space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            string = unicode_to_decimal_w(space, w_value)
            value, w_longval = string_to_int_or_long(space, string)
            ok = True
        else:
            # If object supports the buffer interface
            try:
                w_buffer = space.buffer(w_value)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
            else:
                buf = space.interp_w(Buffer, w_buffer)
                value, w_longval = string_to_int_or_long(space, buf.as_str())
                ok = True

        if not ok:
            # otherwise, use the __int__() or the __trunc__() methods
            w_obj = w_value
            if space.lookup(w_obj, '__int__') is None:
                w_obj = space.trunc(w_obj)
            w_obj = space.int(w_obj)
            # 'int(x)' should return what x.__int__() returned, which should
            # be an int or long or a subclass thereof.
            if space.is_w(w_inttype, space.w_int):
                return w_obj
            # int_w is effectively what we want in this case,
            # we cannot construct a subclass of int instance with an
            # an overflowing long
            try:
                value = space.int_w(w_obj)
            except OperationError, e:
                if e.match(space, space.w_TypeError):
                    raise OperationError(space.w_ValueError,
                        space.wrap("value can't be converted to int"))
                raise e
    else:
        base = space.int_w(w_base)

        if space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            s = unicode_to_decimal_w(space, w_value)
        else:
            try:
                s = space.str_w(w_value)
            except OperationError, e:
                raise OperationError(space.w_TypeError,
                                     space.wrap("int() can't convert non-string "
                                                "with explicit base"))

        value, w_longval = string_to_int_or_long(space, s, base)

    if w_longval is not None:
        if not space.is_w(w_inttype, space.w_int):
            raise OperationError(space.w_OverflowError,
                                 space.wrap(
                "long int too large to convert to int"))
        return w_longval
    elif space.is_w(w_inttype, space.w_int):
        # common case
        return wrapint(space, value)
    else:
        w_obj = space.allocate_instance(W_IntObject, w_inttype)
        W_IntObject.__init__(w_obj, value)
        return w_obj

def descr_get_numerator(space, w_obj):
    return space.int(w_obj)

def descr_get_denominator(space, w_obj):
    return space.wrap(1)

def descr_get_real(space, w_obj):
    return space.int(w_obj)

def descr_get_imag(space, w_obj):
    return space.wrap(0)

# ____________________________________________________________

W_IntObject.typedef = StdTypeDef("int",
    __doc__ = '''int(x[, base]) -> integer

Convert a string or number to an integer, if possible.  A floating point
argument will be truncated towards zero (this does not include a string
representation of a floating point number!)  When converting a string, use
the optional base.  It is an error to supply a base when converting a
non-string. If the argument is outside the integer range a long object
will be returned instead.''',
    __new__ = interp2app(descr__new__),
    conjugate = interp2app(descr_conjugate),
    bit_length = interp2app(descr_bit_length),
    numerator = typedef.GetSetProperty(descr_get_numerator),
    denominator = typedef.GetSetProperty(descr_get_denominator),
    real = typedef.GetSetProperty(descr_get_real),
    imag = typedef.GetSetProperty(descr_get_imag),
    __int__ = interpindirect2app(W_AbstractIntObject.int),
)
int_typedef = W_IntObject.typedef
int_typedef.registermethods(globals())

registerimplementation(W_IntObject)

# NB: This code is shared by smallintobject.py, and thus no other Int
# multimethods should be invoked from these implementations. Instead, add an
# alias and then teach copy_multimethods in smallintobject.py to override
# it. See int__Int for example.

def repr__Int(space, w_int1):
    a = w_int1.intval
    res = str(a)
    return space.wrap(res)

str__Int = repr__Int

def format__Int_ANY(space, w_int, w_format_spec):
    return newformat.run_formatter(space, w_format_spec, "format_int_or_long",
                                   w_int, newformat.INT_KIND)

def declare_new_int_comparison(opname):
    import operator
    from rpython.tool.sourcetools import func_with_new_name
    op = getattr(operator, opname)
    def f(space, w_int1, w_int2):
        i = w_int1.intval
        j = w_int2.intval
        return space.newbool(op(i, j))
    name = "%s__Int_Int" % (opname,)
    return func_with_new_name(f, name), name

for op in ['lt', 'le', 'eq', 'ne', 'gt', 'ge']:
    func, name = declare_new_int_comparison(op)
    globals()[name] = func

def hash__Int(space, w_int1):
    # unlike CPython, we don't special-case the value -1 in most of our
    # hash functions, so there is not much sense special-casing it here either.
    # Make sure this is consistent with the hash of floats and longs.
    return w_int1.int(space)

# coerce
def coerce__Int_Int(space, w_int1, w_int2):
    return space.newtuple([w_int1, w_int2])


def add__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x + y)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer addition"))
    return wrapint(space, z)

def sub__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x - y)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer substraction"))
    return wrapint(space, z)

def mul__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x * y)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer multiplication"))
    return wrapint(space, z)

def floordiv__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x // y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer division by zero"))
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer division"))
    return wrapint(space, z)
div__Int_Int = floordiv__Int_Int

def truediv__Int_Int(space, w_int1, w_int2):
    x = float(w_int1.intval)
    y = float(w_int2.intval)
    if y == 0.0:
        raise FailedToImplementArgs(space.w_ZeroDivisionError, space.wrap("float division"))
    return space.wrap(x / y)

def mod__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x % y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer modulo by zero"))
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer modulo"))
    return wrapint(space, z)

def divmod__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x // y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer divmod by zero"))
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer modulo"))
    # no overflow possible
    m = x % y
    w = space.wrap
    return space.newtuple([w(z), w(m)])


# helper for pow()
@jit.look_inside_iff(lambda space, iv, iw, iz:
                     jit.isconstant(iw) and jit.isconstant(iz))
def _impl_int_int_pow(space, iv, iw, iz):
    if iw < 0:
        if iz != 0:
            raise OperationError(space.w_TypeError,
                             space.wrap("pow() 2nd argument "
                 "cannot be negative when 3rd argument specified"))
        ## bounce it, since it always returns float
        raise FailedToImplementArgs(space.w_ValueError,
                                space.wrap("integer exponentiation"))
    temp = iv
    ix = 1
    try:
        while iw > 0:
            if iw & 1:
                ix = ovfcheck(ix*temp)
            iw >>= 1   #/* Shift exponent down by 1 bit */
            if iw==0:
                break
            temp = ovfcheck(temp*temp) #/* Square the value of temp */
            if iz:
                #/* If we did a multiplication, perform a modulo */
                ix = ix % iz;
                temp = temp % iz;
        if iz:
            ix = ix % iz
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer exponentiation"))
    return ix

def pow__Int_Int_Int(space, w_int1, w_int2, w_int3):
    x = w_int1.intval
    y = w_int2.intval
    z = w_int3.intval
    if z == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("pow() 3rd argument cannot be 0"))
    return space.wrap(_impl_int_int_pow(space, x, y, z))

def pow__Int_Int_None(space, w_int1, w_int2, w_int3):
    x = w_int1.intval
    y = w_int2.intval
    return space.wrap(_impl_int_int_pow(space, x, y, 0))

def neg__Int(space, w_int1):
    a = w_int1.intval
    try:
        x = ovfcheck(-a)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer negation"))
    return wrapint(space, x)
get_negint = neg__Int


def abs__Int(space, w_int1):
    if w_int1.intval >= 0:
        return w_int1.int(space)
    else:
        return get_negint(space, w_int1)

def nonzero__Int(space, w_int1):
    return space.newbool(w_int1.intval != 0)

def invert__Int(space, w_int1):
    x = w_int1.intval
    a = ~x
    return wrapint(space, a)

def lshift__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    if r_uint(b) < LONG_BIT: # 0 <= b < LONG_BIT
        try:
            c = ovfcheck(a << b)
        except OverflowError:
            raise FailedToImplementArgs(space.w_OverflowError,
                                    space.wrap("integer left shift"))
        return wrapint(space, c)
    if b < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    else: #b >= LONG_BIT
        if a == 0:
            return w_int1.int(space)
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer left shift"))

def rshift__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    if r_uint(b) >= LONG_BIT: # not (0 <= b < LONG_BIT)
        if b < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("negative shift count"))
        else: # b >= LONG_BIT
            if a == 0:
                return w_int1.int(space)
            if a < 0:
                a = -1
            else:
                a = 0
    else:
        a = a >> b
    return wrapint(space, a)

def and__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a & b
    return wrapint(space, res)

def xor__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a ^ b
    return wrapint(space, res)

def or__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a | b
    return wrapint(space, res)

def pos__Int(self, space):
    return self.int(space)
trunc__Int = pos__Int

def index__Int(space, w_int1):
    return w_int1.int(space)

def float__Int(space, w_int1):
    a = w_int1.intval
    x = float(a)
    return space.newfloat(x)

def oct__Int(space, w_int1):
    return space.wrap(oct(w_int1.intval))

def hex__Int(space, w_int1):
    return space.wrap(hex(w_int1.intval))

def getnewargs__Int(space, w_int1):
    return space.newtuple([wrapint(space, w_int1.intval)])


register_all(vars())
