

USE_GMP = False


if USE_GMP:
    xxx
else:
    from pypy.rlib._rbigint_native import rbigint, parse_digit_string
