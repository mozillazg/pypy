
from pypy.conftest import gettestobjspace
from pypy.objspace.std.test.test_listobject import TestW_ListObject,\
     AppTestW_ListObject

class TestW_ListMultiObject(TestW_ListObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{'objspace.std.withmultilist': True})

class AppTestMultiList(AppTestW_ListObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{'objspace.std.withmultilist': True})
    
