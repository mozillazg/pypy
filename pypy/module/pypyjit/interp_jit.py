"""This is not the JIT :-)

This is transformed to become a JIT by code elsewhere: pypy/jit/*
"""
import py
import sys
from pypy.tool.pairtype import extendabletype
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.rlib.jit import hint, _is_early_constant, JitDriver
import pypy.interpreter.pyopcode   # for side-effects
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, Arguments
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

    def compute_invariants(self, reds, next_instr, pycode):
        # compute the information that really only depends on next_instr
        # and pycode
        frame = reds.frame
        valuestackdepth = frame.valuestackdepth
        blockstack = frame.blockstack
        return (valuestackdepth, blockstack)

    def on_enter_jit(self, invariants, reds, next_instr, pycode):
        # *loads* of nonsense for now
        (depth, oldblockstack) = invariants
        frame = reds.frame
        pycode = hint(pycode, deepfreeze=True)

        fastlocals_w = [None] * pycode.co_nlocals

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

        # XXX we should also make a completely virtual copy of oldblockstack

pypyjitdriver = PyPyJitDriver()

class __extend__(PyFrame):

    def dispatch(self, pycode, next_instr, ec):
        next_instr = r_uint(next_instr)
        try:
            while True:
                pypyjitdriver.jit_merge_point(
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
        pypyjitdriver.can_enter_jit(frame=f, ec=ec, next_instr=jumpto,
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

def jit_startup(space, argv):
    # save the app-level sys.executable in JITInfo, where the machine
    # code backend can fish for it.  A bit hackish.
    from pypy.jit.codegen.hlinfo import highleveljitinfo
    highleveljitinfo.sys_executable = argv[0]

    # recognize the option  --jit PARAM=VALUE,PARAM=VALUE...
    # if it is at the beginning.  A bit ad-hoc.
    if len(argv) > 2 and argv[1] == '--jit':
        argv.pop(1)
        try:
            pypyjitdriver.set_user_param(argv.pop(1))
        except ValueError:
            from pypy.rlib.debug import debug_print
            debug_print("WARNING: invalid --jit parameters string")


def set_param(space, args):
    '''Configure the tunable JIT parameters.
        * set_param(name=value, ...)            # as keyword arguments
        * set_param("name=value,name=value")    # as a user-supplied string
    '''
    args_w, kwds_w = args.unpack()
    if len(args_w) > 1:
        msg = ("set_param() takes at most 1 non-keyword argument, %d given"
               % len(args_w))
        raise OperationError(space.w_TypeError, space.wrap(msg))
    if len(args_w) == 1:
        text = space.str_w(args_w[0])
        try:
            pypyjitdriver.set_user_param(text)
        except ValueError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("error in JIT parameters string"))
    for key, w_value in kwds_w.items():
        intval = space.int_w(w_value)
        try:
            pypyjitdriver.set_param(key, intval)
        except ValueError:
            raise OperationError(space.w_TypeError,
                                 space.wrap("no JIT parameter '%s'" % (key,)))

set_param.unwrap_spec = [ObjSpace, Arguments]
