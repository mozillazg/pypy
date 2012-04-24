import py

from pypy.rlib import rerased_raw, longlong2float
from pypy.rpython.annlowlevel import hlstr
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin


class TestUntypedStorageDirect(object):
    def test_int(self):
        storage = rerased_raw.UntypedStorage("ii")

        storage.setint(0, 2)
        assert storage.getint(0) == 2

        storage.setint(1, 5)
        assert storage.getint(1) == 5

    def test_float(self):
        storage = rerased_raw.UntypedStorage("f")
        storage.setfloat(0, 5.5)

        assert storage.getfloat(0) == 5.5

    def test_bool(self):
        storage = rerased_raw.UntypedStorage("bi")
        storage.setbool(0, True)

        assert storage.getbool(0) is True

    def test_instance(self):
        class A(object):
            def __init__(self, value):
                self.value = value

        storage = rerased_raw.UntypedStorage("o")
        storage.setinstance(0, A(4))

        assert storage.getinstance(0, A).value == 4

    def test_str(self):
        storage = rerased_raw.UntypedStorage("s")
        storage.setstr(0, "abc")

        assert storage.getstr(0) == "abc"

    def test_unicode(self):
        storage= rerased_raw.UntypedStorage("u")
        storage.setunicode(0, u"abc")

        assert storage.getunicode(0) == u"abc"

    def test_getlength(self):
        storage = rerased_raw.UntypedStorage("ooi")
        assert storage.getlength() == 3

    def test_getshape(self):
        storage = rerased_raw.UntypedStorage("ooi")
        assert storage.getshape() == "ooi"

class BaseTestUntypedStorage(BaseRtypingTest):
    def test_int(self):
        def f(x):
            storage = rerased_raw.UntypedStorage("i")
            storage.setint(0, x)
            return storage.getint(0)

        res = self.interpret(f, [4])
        assert res == 4

    def test_bool(self):
        def f(x):
            storage = rerased_raw.UntypedStorage("b")
            storage.setbool(0, x)
            return storage.getbool(0)

        res = self.interpret(f, [True])
        assert res == True

    def test_float(self):
        def f(x):
            storage = rerased_raw.UntypedStorage("f")
            storage.setfloat(0, x)
            return storage.getfloat(0)

        res = self.interpret(f, [12.3])
        assert res == 12.3

    def test_instance(self):
        class A(object):
            def __init__(self, v):
                self.v = v

        def f(x):
            storage = rerased_raw.UntypedStorage("o")
            storage.setinstance(0, A(x))
            return storage.getinstance(0, A).v

        res = self.interpret(f, [27])
        assert res == 27

    def test_str(self):
        data = ["abc"]
        def f(i):
            storage = rerased_raw.UntypedStorage("s")
            storage.setstr(0, data[i])
            return storage.getstr(0)

        res = self.interpret(f, [0])
        assert self.ll_to_string(res) == "abc"

    def test_unicode(self):
        data = [u"abc"]
        def f(i):
            storage = rerased_raw.UntypedStorage("u")
            storage.setunicode(0, data[i])
            return storage.getunicode(0)

        res = self.interpret(f, [0])
        assert self.ll_to_string(res) == "abc"


    def test_exception_catching(self):
        class A(object):
            def __init__(self, v):
                self.v = v

        def f(x):
            try:
                storage = rerased_raw.UntypedStorage("io")
                storage.setint(0, x)
                value1 = storage.getint(0)
                storage.setinstance(1, A(x))
                value2 = storage.getinstance(1, A)
                return value1 + value2.v
            except Exception:
                return 50000

        res = self.interpret(f, [4])
        assert res == 8

    def test_union(self):
        def f(x, v):
            if x:
                storage = rerased_raw.UntypedStorage("i")
            else:
                storage = rerased_raw.UntypedStorage("ii")
            storage.setint(0, v)
            return storage.getint(0)

        res = self.interpret(f, [True, 15])
        assert res == 15

    def test_getlength(self):
        def f():
            storage = rerased_raw.UntypedStorage("ooi")
            return storage.getlength()

        res = self.interpret(f, [])
        assert res == 3

    def test_getshape(self):
        def f():
            storage = rerased_raw.UntypedStorage("ooi")
            return storage.getshape()

        llres = self.interpret(f, [])
        assert self.ll_to_string(llres) == "ooi"

    def test_const(self):
        class A(object):
            def __init__(self, v):
                self.v = v
        storage = rerased_raw.UntypedStorage("io")
        storage.setint(0, 1)
        storage.setinstance(1, A(20))
        def f(i):
            A(i)
            if i:
                local_storage = rerased_raw.UntypedStorage("ii")
            else:
                local_storage = storage
            return local_storage.getint(0) + local_storage.getinstance(1, A).v

        res = self.interpret(f, [0])
        assert res == 21

    def test_const_types(self):
        storage = rerased_raw.UntypedStorage("bfsu")
        storage.setbool(0, True)
        storage.setfloat(1, 2.5)
        storage.setstr(2, "hello")
        storage.setunicode(3, u"world!")

        def f(i):
            if i:
                local_storage = rerased_raw.UntypedStorage("o")
            else:
                local_storage = storage
            return (local_storage.getbool(0) + local_storage.getfloat(1) +
                    len(local_storage.getstr(2)) + len(local_storage.getunicode(3)))

        res = self.interpret(f, [0])
        assert res == 14.5

    def test_enumerate_elements(self):
        def f():
            storage = rerased_raw.UntypedStorage("sibf")
            storage.setint(1, 13)
            storage.setstr(0, "abc")
            storage.setfloat(3, 3.5)
            storage.setbool(2, True)
            return storage

        llres = self.interpret(f, [])._obj
        lst = list(rerased_raw.ll_enumerate_elements(llres))
        assert hlstr(lst[0][1]) == "abc"
        assert lst[0][0] == 0
        assert lst[1:3] == [(1, 13), (2, True)]
        assert lst[3][0] == 3
        assert longlong2float.longlong2float(lst[3][1]) == 3.5

class TestUntypedStorageLLtype(LLRtypeMixin, BaseTestUntypedStorage):
    pass
