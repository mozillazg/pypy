from pypy.objspace.std.test import test_userobject

WITH_BUILTINSHORTCUT = {'objspace.std.builtinshortcut': True}

class AppTestUserObject(test_userobject.AppTestUserObject):
    OPTIONS = WITH_BUILTINSHORTCUT

class AppTestWithMultiMethodVersion2(test_userobject.AppTestWithMultiMethodVersion2):
    OPTIONS = WITH_BUILTINSHORTCUT

class AppTestBug:
    def setup_class(cls):
        from pypy import conftest
        cls.space = conftest.gettestobjspace(**WITH_BUILTINSHORTCUT)

    def test_frozen_subtype(self):
        skip("in-progress")
        class S(set): pass
        assert S("abc") == set("abc")
        assert set("abc") == S("abc")
        class F(frozenset): pass
        assert F("abc") == frozenset("abc")
        assert frozenset("abc") == F("abc")
