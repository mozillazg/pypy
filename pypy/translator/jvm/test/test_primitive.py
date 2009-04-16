import os
import time
import py

from pypy.translator.jvm.test.runtest import JvmTest

class TestPrimitive(JvmTest):

    def test_time_time(self):
        def fn():
            return time.time()
        t1 = self.interpret(fn, [])
        t2 = self.interpret(fn, [])
        assert t1 <= t2

    def test_rffi_primitive(self):
        from pypy.rpython.lltypesystem import rffi, lltype
        from pypy.translator.tool.cbuild import ExternalCompilationInfo
        eci = ExternalCompilationInfo(
            includes = ['ctype.h']
        )
        tolower = rffi.llexternal('tolower', [lltype.Signed], lltype.Signed,
                                  compilation_info=eci,
                                  oo_primitive='tolower')
        assert tolower._ptr._obj.oo_primitive == 'tolower'

        def fn(n):
            return tolower(n)
        res = self.interpret(fn, [ord('A')])
        assert res == ord('a')
