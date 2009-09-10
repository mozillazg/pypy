
from pypy.lang.js.test.test_interp import assertv

def test_infinity_nan():
    assertv('1/0', 'Infinity')
    assertv('0/0', 'NaN')
    assertv('-1/0', '-Infinity')

def test_overflow_int_to_float():
    assertv('1e200', '1e+200')
