from pypy.objspace.std.test import test_userobject

class AppTestUserObject(test_userobject.AppTestUserObject):
    OPTIONS = {'objspace.std.builtinshortcut': True}

class AppTestWithMultiMethodVersion2(test_userobject.AppTestWithMultiMethodVersion2):
    OPTIONS = {'objspace.std.builtinshortcut': True}
