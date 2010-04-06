
from pypy.module.cpyext.api import register_c_function

for name in ['Py_FatalError', 'PyOS_snprintf', 'PyOS_vsnprintf']:
    register_c_function(name)
