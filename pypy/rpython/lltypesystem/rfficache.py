
""" This file creates and maintains _cache/rtypes.py, which
keeps information about C type sizes on various platforms
"""

import py
from pypy.translator.tool.cbuild import build_executable
from subprocess import PIPE, Popen
from pypy.tool.udir import udir

def sizeof_c_type(c_typename, includes={}):
    includes['stdio.h'] = True
    include_string = "\n".join(["#include <%s>" % i for i in includes.keys()])
    c_source = py.code.Source('''
    // includes
    %s

    // checking code
    int main(void)
    {
       printf("%%d\\n", sizeof(%s));
       return (0);
    }
    ''' % (include_string, c_typename))
    c_file = udir.join("typetest.c")
    c_file.write(c_source)

    c_exec = build_executable([str(c_file)])
    pipe = Popen(c_exec, stdout=PIPE)
    pipe.wait()
    return int(pipe.stdout.read()) * 8
