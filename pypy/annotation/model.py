"""
This file defines the 'subset' SomeValue classes.

An instance of a SomeValue class stands for a Python object that has some
known properties, for example that is known to be a list of non-negative
integers.  Each instance can be considered as an object that is only
'partially defined'.  Another point of view is that each instance is a
generic element in some specific subset of the set of all objects.

"""

# Old terminology still in use here and there:
#    SomeValue means one of the SomeXxx classes in this file.
#    Cell is an instance of one of these classes.
#
# Think about cells as potato-shaped circles in a diagram:
#    ______________________________________________________
#   / SomeObject()                                         \
#  /   ___________________________          ______________  \
#  |  / SomeInteger(nonneg=False) \____    / SomeString() \  \
#  | /     __________________________  \   |              |  |
#  | |    / SomeInteger(nonneg=True) \ |   |      "hello" |  |
#  | |    |   0    42       _________/ |   \______________/  |
#  | \ -3 \________________/           /                     |
#  \  \                     -5   _____/                      /
#   \  \________________________/              3.1416       /
#    \_____________________________________________________/
#


from pypy.annotation.pairtype import pair


class SomeObject:
    """The set of all objects.  Each instance stands
    for an arbitrary object about which nothing is known."""
    knowntype = None
    def __eq__(self, other):
        return (self.__class__, self.__dict__) == (other.__class__, other.__dict__)
    def __ne__(self, other):
        return not (self == other)
    def contains(self, other):
        return pair(self, other).union() == self

class SomeInteger(SomeObject):
    "Stands for an object which is known to be an integer."
    knowntype = int
    def __init__(self, nonneg=False):
        self.nonneg = nonneg

class SomeBool(SomeInteger):
    "Stands for true or false."
    knowntype = bool
    def __init__(self):
        SomeInteger.__init__(nonneg=True)

class SomeString(SomeObject):
    "Stands for an object which is known to be a string."
    knowntype = str

class SomeList(SomeObject):
    "Stands for a homogenous list of any length."
    knowntype = list
    def __init__(self, factories, s_item=SomeObject()):
        self.factories = factories
        self.s_item = s_item     # general enough for any element

class SomeTuple(SomeObject):
    "Stands for a tuple of known length."
    knowntype = tuple
    def __init__(self, items):
        self.items = tuple(items)   # tuple of s_xxx elements

class SomeImpossibleValue(SomeObject):
    """The empty set.  Instances are placeholders for objects that
    will never show up at run-time, e.g. elements of an empty list."""


def immutablevalue(x):
    "The most precise SomeValue instance that contains the immutable value x."
    if isinstance(bool, type) and isinstance(x, bool):
        return SomeBool()
    elif isinstance(x, int):
        return SomeInteger(nonneg = x>=0)
    elif isinstance(x, str):
        return SomeString()
    elif isinstance(x, tuple):
        return SomeTuple(items = [immutablevalue(e) for e in x])
    else:
        return SomeObject()

def valueoftype(t):
    "The most precise SomeValue instance that contains all objects of type t."
    if isinstance(bool, type) and issubclass(t, bool):
        return SomeBool()
    elif issubclass(t, int):
        return SomeInteger()
    elif issubclass(t, str):
        return SomeString()
    elif issubclass(t, list):
        return SomeList(factories={})


# this has the side-effect of registering the binary operations
from pypy.annotation.binaryop import BINARY_OPERATIONS
