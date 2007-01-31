"""This is not the JIT :-)

The pypyjit module helpers set the 'jit_enable' flag on code objects.
The code below makes two identical copies of the interpreter's main
loop, and the flag controls which of them is used.  One of them
(dispatch_jit) is transformed to become a JIT by code elsewhere:
pypy/jit/*
"""
import py
import pypy.interpreter.pyopcode   # for side-effects
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.pyframe import PyFrame
from pypy.tool.sourcetools import func_with_new_name


PyCode.jit_enable = False     # new default attribute
super_dispatch = PyFrame.dispatch


def setup():
    # make a copy of dispatch in which JITTING is True
    # (hack hack!)
    src2 = py.code.Source(PyFrame.dispatch)
    hdr = src2[0].strip()
    assert hdr == 'def dispatch(self, pycode, next_instr, ec):'
    src2 = src2[1:].deindent()

    src2 = src2.putaround(
                  "def maker(JITTING):\n"
                  "  def dispatch_jit(self, pycode, next_instr, ec):\n",
                  "#\n" # for indentation :-(
                  "  return dispatch_jit")
    print src2
    d = {}
    exec src2.compile() in super_dispatch.func_globals, d
    PyFrame.dispatch_jit = d['maker'](JITTING=True)

    class __extend__(PyFrame):

        def dispatch(self, pycode, next_instr, ec):
            if pycode.jit_enable:
                return self.dispatch_jit(pycode, next_instr, ec)
            else:
                return super_dispatch(self, pycode, next_instr, ec)

setup()

PORTAL = PyFrame.dispatch_jit

# ____________________________________________________________
#
# Public interface

def enable(space, w_code, w_enabled=True):
    # save the app-level sys.executable in JITInfo, where the machine
    # code backend can fish for it - XXX the following import will look
    # less obscure once codebuf.py is moved to a general
    # processor-independent place
    from pypy.jit.codegen.hlinfo import highleveljitinfo
    if highleveljitinfo.sys_executable is None:
        highleveljitinfo.sys_executable = space.str_w(
            space.sys.get('executable'))

    code = space.interp_w(PyCode, w_code)
    code.jit_enable = space.is_true(w_enabled)
