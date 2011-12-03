"""This module defines an object type which can efficiently represent
an array of basic values: characters, integers, floating point
numbers.  Arrays are sequence types and behave very much like lists,
except that the type of objects stored in them is constrained.  The
type is specified at object creation time by using a type code, which
is a single character.  The following type codes are defined:

    Type code   C Type             Minimum size in bytes 
    'c'         character          1 
    'b'         signed integer     1 
    'B'         unsigned integer   1 
    'u'         Unicode character  2 
    'h'         signed integer     2 
    'H'         unsigned integer   2 
    'i'         signed integer     2 
    'I'         unsigned integer   2 
    'l'         signed integer     4 
    'L'         unsigned integer   4 
    'f'         floating point     4 
    'd'         floating point     8 

The constructor is:

array(typecode [, initializer]) -- create a new array
"""

# indirection needed; otherwise the built-in module "array" shadows
# any file array.py that would be found in the user dirs
try:
    from __builtin_array import *
except ImportError:
    from _array import array, ArrayType
