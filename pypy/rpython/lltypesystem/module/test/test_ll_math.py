""" Try to test systematically all cases of ll_math.py.
"""

from pypy.rpython.lltypesystem.module import ll_math
from pypy.rlib.rarithmetic import isinf, isnan, INFINITY, NAN
import math

def positiveinf(x):
    return isinf(x) and x > 0.0

def negativeinf(x):
    return isinf(x) and x < 0.0

def finite(x):
    return not isinf(x) and not isnan(x)


class TestMath:

    REGCASES = [
        (name, (0.3,), getattr(math, name)(0.3))
        for name in ll_math.unary_math_functions]

    IRREGCASES = [
        ('atan2', (0.31, 0.123), math.atan2(0.31, 0.123)),
        ('fmod',  (0.31, 0.123), math.fmod(0.31, 0.123)),
        ('hypot', (0.31, 0.123), math.hypot(0.31, 0.123)),
        ('pow',   (0.31, 0.123), math.pow(0.31, 0.123)),
        ('ldexp', (3.375, 2), 13.5),
        ('ldexp', (1.0, -10000), 0.0),   # underflow
        ]

    OVFCASES = [
        ('cosh', (9999.9,), OverflowError),
        ('sinh', (9999.9,), OverflowError),
        ('exp', (9999.9,), OverflowError),
        ('pow', (10.0, 40000.0), OverflowError),
        ('ldexp', (10.0, 40000), OverflowError),
        ]

    INFCASES = [
        ('acos', (INFINITY,), ValueError),
        ('acos', (-INFINITY,), ValueError),
        ('asin', (INFINITY,), ValueError),
        ('asin', (-INFINITY,), ValueError),
        ('atan', (INFINITY,), math.pi / 2),
        ('atan', (-INFINITY,), -math.pi / 2),
        ('ceil', (INFINITY,), positiveinf),
        ('ceil', (-INFINITY,), negativeinf),
        ('cos', (INFINITY,), ValueError),
        ('cos', (-INFINITY,), ValueError),
        ('cosh', (INFINITY,), positiveinf),
        ('cosh', (-INFINITY,), positiveinf),
        ('exp', (INFINITY,), positiveinf),
        ('exp', (-INFINITY,), 0.0),
        ('fabs', (INFINITY,), positiveinf),
        ('fabs', (-INFINITY,), positiveinf),
        ('floor', (INFINITY,), positiveinf),
        ('floor', (-INFINITY,), negativeinf),
        ('sin', (INFINITY,), ValueError),
        ('sin', (-INFINITY,), ValueError),
        ('sinh', (INFINITY,), positiveinf),
        ('sinh', (-INFINITY,), negativeinf),
        ('sqrt', (INFINITY,), positiveinf),
        ('sqrt', (-INFINITY,), ValueError),
        ('tan', (INFINITY,), ValueError),
        ('tan', (-INFINITY,), ValueError),
        ('tanh', (INFINITY,), 1.0),
        ('tanh', (-INFINITY,), -1.0),
        ]

    NANREGCASES = [
        (name, (NAN,), isnan) for name in ll_math.unary_math_functions]

    NANIRREGCASES = []

    TESTCASES = (REGCASES + IRREGCASES + OVFCASES
                 + INFCASES + NANREGCASES + NANIRREGCASES)


def make_test_case((fnname, args, expected), dict):
    #
    def test_func(self):
        fn = getattr(ll_math, 'll_math_' + fnname)
        repr = "%s(%s)" % (fnname, ', '.join(map(str, args)))
        try:
            got = fn(*args)
        except ValueError:
            assert expected == ValueError, "%s: got a ValueError" % (repr,)
        except OverflowError:
            assert expected == OverflowError, "%s: got an OverflowError" % (
                repr,)
        else:
            if callable(expected):
                ok = expected(got)
            else:
                ok = finite(got) and got == expected
            if not ok:
                raise AssertionError("%r: got %s" % (repr, got))
    #
    dict[fnname] = dict.get(fnname, 0) + 1
    testname = 'test_%s_%d' % (fnname, dict[fnname])
    test_func.func_name = testname
    setattr(TestMath, testname, test_func)

_d = {}
for testcase in TestMath.TESTCASES:
    make_test_case(testcase, _d)
