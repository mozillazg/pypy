import autopath
from py.test import raises

from pypy.objspace.std.multimethod import *


class W_Root(object):
    pass

class W_IntObject(W_Root):
    pass

class W_BoolObject(W_Root):
    pass

class W_StringObject(W_Root):
    pass

def delegate_b2i(w_x):
    assert isinstance(w_x, W_BoolObject)
    return W_IntObject()

add = MultiMethodTable(2, root_class=W_Root, argnames_before=['space'])

def add__Int_Int(space, w_x, w_y):
    assert space == 'space'
    assert isinstance(w_x, W_IntObject)
    assert isinstance(w_y, W_IntObject)
    return 'fine'

add.register(add__Int_Int, W_IntObject, W_IntObject)


def setup_module(mod):
    typeorder = {
        W_IntObject: [(W_IntObject, None)],
        W_BoolObject: [(W_BoolObject, None), (W_IntObject, delegate_b2i)],
        W_StringObject: [(W_StringObject, None)],
        }
    mod.add1 = add.install('__add', [typeorder, typeorder])


def test_simple():
    space = 'space'
    w_x = W_IntObject()
    w_y = W_IntObject()
    assert add1(space, w_x, w_y) == 'fine'

def test_failtoimplement():
    space = 'space'
    w_x = W_IntObject()
    w_s = W_StringObject()
    raises(FailedToImplement, "add1(space, w_x, w_s)")
    raises(FailedToImplement, "add1(space, w_s, w_x)")

def test_delegate():
    space = 'space'
    w_x = W_IntObject()
    w_s = W_StringObject()
    w_b = W_BoolObject()
    assert add1(space, w_x, w_b) == 'fine'
    assert add1(space, w_b, w_x) == 'fine'
    assert add1(space, w_b, w_b) == 'fine'
    raises(FailedToImplement, "add1(space, w_b, w_s)")
    raises(FailedToImplement, "add1(space, w_s, w_b)")
