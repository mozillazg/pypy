from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys

class AppTestTypeObject(AppTestCpythonExtensionBase):
    def test_typeobject(self):
        import sys
        module = self.import_module(name='foo')
        assert 'foo' in sys.modules
        assert "copy" in dir(module.fooType)
        obj = module.new()
        print obj.foo
        assert obj.foo == 42
        print "Obj has type", type(obj)
        assert type(obj) is module.fooType
        print "type of obj has type", type(type(obj))
        obj2 = obj.copy()
        assert module.new().name == "Foo Example"
        c = module.fooType.copy
        assert not "im_func" in dir(module.fooType.copy)
        assert module.fooType.copy.__objclass__ is module.fooType
        assert "copy" in repr(module.fooType.copy)
        assert repr(module.fooType) == "<type 'foo.foo'>"
        assert repr(obj2) == "<Foo>"
        assert repr(module.fooType.__call__) == "<slot wrapper '__call__' of 'foo' objects>"
        assert obj2(foo=1, bar=2) == dict(foo=1, bar=2)

        print obj.foo
        assert obj.foo == 42
        assert obj.int_member == obj.foo
        obj.int_member = 23
        assert obj.int_member == 23
        raises(TypeError, "obj.int_member_readonly = 42")
        raises(SystemError, "obj.broken_member")
        raises(SystemError, "obj.broken_member = 42")
