import py

from pypy.rlib import rerased_raw
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin


def test_direct_int():
    storage = rerased_raw.UntypedStorage(2)

    storage.setint(0, 2)
    assert storage.getint(0) == 2

    storage.setint(1, 5)
    assert storage.getint(1) == 5

def test_direct_instance():
    class A(object):
        def __init__(self, value):
            self.value = value

    storage = rerased_raw.UntypedStorage(1)
    storage.setinstance(0, A(4))

    assert storage.getinstance(A, 0).value == 4


class TestRerasedRawLLType(LLRtypeMixin, BaseRtypingTest):
    def test_int(self):
        def f(x):
            storage = rerased_raw.UntypedStorage(1)
            storage.setint(0, x)
            return storage.getint(0)

        res = self.interpret(f, [4])
        assert res == 4