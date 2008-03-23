"""This is not the JIT :-)

The pypyjit module helpers set the 'jit_enable' flag on code objects.
The code below makes two identical copies of the interpreter's main
loop, and the flag controls which of them is used.  One of them
(dispatch_jit) is transformed to become a JIT by code elsewhere:
pypy/jit/*
"""
import py
import sys
from pypy.tool.pairtype import extendabletype
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.rlib.jit import hint, _is_early_constant, JitDriver
import pypy.interpreter.pyopcode   # for side-effects
from pypy.interpreter.gateway import ObjSpace
from pypy.interpreter.eval import Frame
from pypy.interpreter.pycode import PyCode, CO_VARARGS, CO_VARKEYWORDS
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.function import Function
from pypy.interpreter.pyopcode import Return, Yield


Frame._virtualizable_ = True
PyCode.jit_enable = False     # new default attribute
super_dispatch = PyFrame.dispatch

class PyPyJitDriver(JitDriver):
    reds = ['frame', 'ec']
    greens = ['next_instr', 'pycode']
    def on_enter_jit(self):
        # *loads* of nonsense for now
        frame = self.frame
        pycode = self.pycode
        pycode = hint(pycode, promote=True)    # xxx workaround
        pycode = hint(pycode, deepfreeze=True)

        fastlocals_w = [None] * pycode.co_nlocals

        stuff = frame.valuestackdepth
        if len(frame.blockstack):
            stuff |= (-sys.maxint-1)

        stuff = hint(stuff, promote=True)
        if stuff >= 0:
            # blockdepth == 0, common case
            # XXX or it was at some point but not now, not at all
            # XXX as we expect to *be* in a loop...
            frame.blockstack = []
        depth = stuff & sys.maxint

        i = pycode.co_nlocals
        while True:
            i -= 1
            if i < 0:
                break
            hint(i, concrete=True)
            w_obj = frame.fastlocals_w[i]
            fastlocals_w[i] = w_obj

        frame.pycode = pycode
        frame.valuestackdepth = depth

        frame.fastlocals_w = fastlocals_w

        virtualstack_w = [None] * pycode.co_stacksize
        while depth > 0:
            depth -= 1
            hint(depth, concrete=True)
            virtualstack_w[depth] = frame.valuestack_w[depth]
        frame.valuestack_w = virtualstack_w

    def getcurrentthreshold():
        return pypyjitconfig.cur_threshold
    getcurrentthreshold = staticmethod(getcurrentthreshold)

class __extend__(PyFrame):

    def dispatch(self, pycode, next_instr, ec):
        next_instr = r_uint(next_instr)
        try:
            while True:
                PyPyJitDriver.jit_merge_point(
                    frame=self, ec=ec, next_instr=next_instr, pycode=pycode)
                pycode = hint(pycode, deepfreeze=True)
                co_code = pycode.co_code
                next_instr = self.handle_bytecode(co_code, next_instr, ec)
        except Return:
            w_result = self.popvalue()
            self.blockstack = None
            self.valuestack_w = None
            return w_result
        except Yield:
            w_result = self.popvalue()
            return w_result

    def JUMP_ABSOLUTE(f, jumpto, next_instr, *ignored):
        ec = f.space.getexecutioncontext()
        PyPyJitDriver.can_enter_jit(frame=f, ec=ec, next_instr=jumpto,
                                    pycode=f.getcode())
        return jumpto

class __extend__(Function):
    __metaclass__ = extendabletype

    def getcode(self):
        # if the self is a compile time constant and if its code
        # is a BuiltinCode => grab and return its code as a constant
        if _is_early_constant(self):
            from pypy.interpreter.gateway import BuiltinCode
            code = hint(self, deepfreeze=True).code
            if not isinstance(code, BuiltinCode): code = self.code
        else:
            code = self.code
        return code
        

# ____________________________________________________________
#
# Public interface

class PyPyJITConfig:
    def __init__(self):
        self.cur_threshold = sys.maxint    # disabled until the space is ready
        self.configured_threshold = JitDriver.getcurrentthreshold()

    def isenabled(self):
        return self.cur_threshold < sys.maxint

    def enable(self):
        self.cur_threshold = self.configured_threshold

    def disable(self):
        self.cur_threshold = sys.maxint

    def setthreshold(self, threshold):
        self.configured_threshold = threshold
        if self.isenabled():
            self.cur_threshold = threshold

    def getthreshold(self):
        return self.configured_threshold

pypyjitconfig = PyPyJITConfig()


def startup(space):
    # save the app-level sys.executable in JITInfo, where the machine
    # code backend can fish for it.  A bit hackish.
    from pypy.jit.codegen.hlinfo import highleveljitinfo
    highleveljitinfo.sys_executable = space.str_w(
        space.sys.get('executable'))
    # -- for now, we start disabled and you have to use pypyjit.enable()
    #pypyjitconfig.enable()


def setthreshold(space, threshold):
    pypyjitconfig.setthreshold(threshold)
setthreshold.unwrap_spec = [ObjSpace, int]

def getthreshold(space):
    return space.wrap(pypyjitconfig.getthreshold())

def enable(space):
    pypyjitconfig.enable()

def disable(space):
    pypyjitconfig.disable()

def isenabled(space):
    return space.newbool(pypyjitconfig.isenabled())
