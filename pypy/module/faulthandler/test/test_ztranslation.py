import sys, py
if sys.platform == 'win32':
    py.test.skip('vmprof disabled on windows')

from pypy.objspace.fake.checkmodule import checkmodule

def test_faulthandler_translates():
    import pypy.module._vmprof.interp_vmprof   # register_code_object_class()
    checkmodule('faulthandler')
