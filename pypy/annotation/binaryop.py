"""
Binary operations between SomeValues.
"""

from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool
from pypy.annotation.model import SomeString, SomeList
from pypy.annotation.model import SomeTuple, SomeImpossibleValue
from pypy.annotation.factory import NeedGeneralization


def setunion(d1, d2):
    "Union of two sets represented as dictionaries."
    d = d1.copy()
    d.update(d2)
    return d

def set(it):
    "Turn an iterable into a set."
    d = {}
    for x in it:
        d[x] = True
    return d


BINARY_OPERATIONS = set(['add', 'sub', 'mul', 'getitem', 'setitem',
                         'union'])

def _defaultcase((obj1, obj2), *args):
    return SomeObject()

for name in BINARY_OPERATIONS:
    setattr(pairtype(SomeObject, SomeObject), name, _defaultcase)


class __extend__(pairtype(SomeInteger, SomeInteger)):

    def union((int1, int2)):
        return SomeInteger(nonneg = int1.nonneg and int2.nonneg)

    def add((int1, int2)):
        return SomeInteger(nonneg = int1.nonneg and int2.nonneg)

    def sub((int1, int2)):
        return SomeInteger()


class __extend__(pairtype(SomeBool, SomeBool)):

    def union((boo1, boo2)):
        return SomeBool()


class __extend__(pairtype(SomeString, SomeString)):

    def union((str1, str2)):
        return SomeString()

    def add((str1, str2)):
        return SomeString()


class __extend__(pairtype(SomeList, SomeList)):

    def union((lst1, lst2)):
        return SomeList(setunion(lst1.factories, lst2.factories),
                        s_item = pair(lst1.s_item, lst2.s_item).union())

    add = union


class __extend__(pairtype(SomeTuple, SomeTuple)):

    def union((tup1, tup2)):
        if len(tup1.items) != len(tup2.items):
            return SomeObject()
        else:
            unions = [pair(x,y).union() for x,y in zip(tup1.items, tup2.items)]
            return SomeTuple(items = unions)

    def add((tup1, tup2)):
        return SomeTuple(items = tup1.items + tup2.items)


class __extend__(pairtype(SomeList, SomeInteger)):
    
    def mul((lst1, int2)):
        return lst1

    def getitem((lst1, int2)):
        return lst1.s_item

    def setitem((lst1, int2), value):
        if not lst1.s_item.contains(value):
            raise NeedGeneralization(lst1, value)


class __extend__(pairtype(SomeInteger, SomeList)):
    
    def mul((int1, lst2)):
        return lst2


class __extend__(pairtype(SomeImpossibleValue, SomeObject)):
    def union((imp1, obj2)):
        return obj2

class __extend__(pairtype(SomeObject, SomeImpossibleValue)):
    def union((obj1, imp2)):
        return obj1
