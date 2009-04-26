from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.translator.tool.cbuild import ExternalCompilationInfo
import sys

eci = ExternalCompilationInfo(libraries=['Poc'])
c_invokeMethod = rffi.llexternal('invokeMethod', [rffi.CCHARP], lltype.Void,
                          compilation_info=eci, threadsafe=False)

def invokeMethod(space, method_name):
    res = c_invokeMethod(method_name)

invokeMethod.unwrap_spec = [ObjSpace, str]
