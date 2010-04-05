
from pypy.module.cpyext.api import cpython_api_c

@cpython_api_c()
def Py_FatalError():
    pass

@cpython_api_c()
def PyOS_snprintf():
    pass

@cpython_api_c()
def PyOS_vsnprintf():
    pass
