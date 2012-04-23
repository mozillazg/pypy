
from pypy.rlib.test.test_rerased_raw import BaseTestUntypedStorage
from pypy.translator.c.test.test_genc import compile

class CCompiledMixin(object):
    # for individual tests see
    # ===> ../../../rlib/test/test_rerased_raw.py
    
    def interpret(self, f, args):
        fn = compile(f, [type(arg) for arg in args], gcpolicy='boehm')
        return fn(*args)

    def ll_to_string(self, x):
        return x

class TestUntypedStorage(CCompiledMixin, BaseTestUntypedStorage):
    pass
