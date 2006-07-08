import autopath
from pypy.objspace.std.dictstrobject import W_DictStrObject
from pypy.conftest import gettestobjspace
from pypy.objspace.std.test import test_dictobject

class TestW_DictObject(test_dictobject.TestW_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withstrdict": True})

class AppTest_DictObject(test_dictobject.AppTest_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withstrdict": True})

class TestDictImplementation(test_dictobject.TestDictImplementation):
    def setup_method(self,method):
        self.space = test_dictobject.FakeSpace()
        self.space.DictObjectCls = W_DictStrObject

    
