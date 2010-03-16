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
        ('frexp', (-1.25,), lambda x: x == (-0.625, 1)),
        ('modf',  (4.25,), lambda x: x == (0.25, 4.0)),
        ('modf',  (-4.25,), lambda x: x == (-0.25, -4.0)),
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
        ('frexp', (INFINITY,), lambda x: isinf(x[0])),
        ('ldexp', (INFINITY, 3), positiveinf),
        ('ldexp', (-INFINITY, 3), negativeinf),
        ('modf',  (INFINITY,), lambda x: positiveinf(x[1])),
        ('modf',  (-INFINITY,), lambda x: negativeinf(x[1])),
        ]

    IRREGERRCASES = [
        #
        ('atan2', (INFINITY, -2.3), math.pi / 2),
        ('atan2', (INFINITY, 0.0), math.pi / 2),
        ('atan2', (INFINITY, 3.0), math.pi / 2),
        #('atan2', (INFINITY, INFINITY), ?strange),
        ('atan2', (2.1, INFINITY), 0.0),
        ('atan2', (0.0, INFINITY), 0.0),
        ('atan2', (-0.1, INFINITY), -0.0),
        ('atan2', (-INFINITY, 0.4), -math.pi / 2),
        ('atan2', (2.1, -INFINITY), math.pi),
        ('atan2', (0.0, -INFINITY), math.pi),
        ('atan2', (-0.1, -INFINITY), -math.pi),
        #
        ('fmod', (INFINITY, 1.0), ValueError),
        ('fmod', (1.0, INFINITY), 1.0),
        ('fmod', (1.0, -INFINITY), 1.0),
        ('fmod', (INFINITY, INFINITY), ValueError),
        ]

    binary_math_functions = ['atan2', 'fmod', 'hypot', 'pow']

    NANCASES1 = [
        (name, (NAN,), isnan) for name in ll_math.unary_math_functions]
    NANCASES2 = [
        (name, (NAN, 0.1), isnan) for name in binary_math_functions]
    NANCASES3 = [
        (name, (-0.2, NAN), isnan) for name in binary_math_functions]
    NANCASES4 = [
        (name, (NAN, -INFINITY), isnan) for name in binary_math_functions
                                        if name != 'hypot']
    NANCASES5 = [
        (name, (INFINITY, NAN), isnan) for name in binary_math_functions
                                       if name != 'hypot']
    NANCASES6 = [
        ('frexp', (NAN,), lambda x: isnan(x[0])),
        ('ldexp', (NAN, 2), isnan),
        ('hypot', (NAN, INFINITY), positiveinf),
        ('hypot', (NAN, -INFINITY), positiveinf),
        ('hypot', (INFINITY, NAN), positiveinf),
        ('hypot', (-INFINITY, NAN), positiveinf),
        ('modf', (NAN,), lambda x: (isnan(x[0]) and isnan(x[1]))),
        ]

    TESTCASES = (REGCASES + IRREGCASES + OVFCASES + INFCASES + IRREGERRCASES
                 + NANCASES1 + NANCASES2 + NANCASES3 + NANCASES4 + NANCASES5
                 + NANCASES6)


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
                gotsign = ll_math.math_copysign(1.0, got)
                expectedsign = ll_math.math_copysign(1.0, expected)
                ok = finite(got) and (got == expected and
                                      gotsign == expectedsign)
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
