"""This implements pyjitpl's execution of operations.
"""

import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.rarithmetic import ovfcheck, r_uint, intmask
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp.history import BoxInt, BoxPtr, BoxFloat, check_descr
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.resoperation import rop

# ____________________________________________________________

##def do_force_token(cpu):
##    raise NotImplementedError

##def do_virtual_ref(cpu, box1, box2):
##    raise NotImplementedError

##def do_virtual_ref_finish(cpu, box1, box2):
##    raise NotImplementedError

##def do_debug_merge_point(cpu, box1):
##    from pypy.jit.metainterp.warmspot import get_stats
##    loc = box1._get_str()
##    get_stats().add_merge_point_location(loc)

# ____________________________________________________________


def make_execute_list(cpuclass):
    from pypy.jit.backend.model import AbstractCPU
    from pypy.jit.metainterp.blackhole import BlackholeInterpreter
    if 0:     # enable this to trace calls to do_xxx
        def wrap(fn):
            def myfn(*args):
                print '<<<', fn.__name__
                try:
                    return fn(*args)
                finally:
                    print fn.__name__, '>>>'
            return myfn
    else:
        def wrap(fn):
            return fn
    #
    execute_by_num_args = {}
    for key, value in rop.__dict__.items():
        if not key.startswith('_'):
            if (rop._FINAL_FIRST <= value <= rop._FINAL_LAST or
                rop._GUARD_FIRST <= value <= rop._GUARD_LAST):
                continue
            # find which list to store the operation in, based on num_args
            num_args = resoperation.oparity[value]
            withdescr = resoperation.opwithdescr[value]
            if withdescr and num_args >= 0:
                num_args += 1
            if num_args not in execute_by_num_args:
                execute_by_num_args[num_args] = [None] * (rop._LAST+1)
            execute = execute_by_num_args[num_args]
            #
            if execute[value] is not None:
                raise Exception("duplicate entry for op number %d" % value)
            if key.endswith('_PURE'):
                key = key[:-5]
            name = 'opimpl_' + key.lower()
            if hasattr(BlackholeInterpreter, name):
                func = make_execute_function_with_boxes(
                    key.lower(),
                    getattr(BlackholeInterpreter, name).im_func)
                if func is not None:
                    execute[value] = func
                    continue
            pass   #XXX...
    cpuclass._execute_by_num_args = execute_by_num_args

def make_execute_function_with_boxes(name, func):
    # Make a wrapper for 'func'.  The func is a simple opimpl_xxx function
    # from the BlackholeInterpreter class.  The wrapper is a new function
    # that receives and returns boxed values.
    for argtype in func.argtypes:
        if argtype not in ('i', 'r', 'f'):
            return None
    if func.resulttype not in ('i', 'r', 'f', None):
        return None
    argtypes = unrolling_iterable(func.argtypes)
    resulttype = func.resulttype
    #
    def do(cpu, *argboxes):
        newargs = ()
        for argtype in argtypes:
            argbox = argboxes[0]
            argboxes = argboxes[1:]
            if argtype == 'i':   value = argbox.getint()
            elif argtype == 'r': value = argbox.getptr_base()
            elif argtype == 'f': value = argbox.getfloat()
            newargs = newargs + (value,)
        #
        result = func(*newargs)
        #
        if resulttype == 'i': return BoxInt(result)
        if resulttype == 'r': return BoxPtr(result)
        if resulttype == 'f': return BoxFloat(result)
    #
    return func_with_new_name(do, 'do_' + name)

def get_execute_funclist(cpu, num_args):
    # workaround, similar to the next one
    return cpu._execute_by_num_args[num_args]
get_execute_funclist._annspecialcase_ = 'specialize:memo'

def get_execute_function(cpu, opnum, num_args):
    # workaround for an annotation limitation: putting this code in
    # a specialize:memo function makes sure the following line is
    # constant-folded away.  Only works if opnum and num_args are
    # constants, of course.
    return cpu._execute_by_num_args[num_args][opnum]
get_execute_function._annspecialcase_ = 'specialize:memo'

def has_descr(opnum):
    # workaround, similar to the previous one
    return resoperation.opwithdescr[opnum]
has_descr._annspecialcase_ = 'specialize:memo'


def execute(cpu, opnum, descr, *argboxes):
    # only for opnums with a fixed arity
    if has_descr(opnum):
        check_descr(descr)
        argboxes = argboxes + (descr,)
    else:
        assert descr is None
    func = get_execute_function(cpu, opnum, len(argboxes))
    assert func is not None
    return func(cpu, *argboxes)
execute._annspecialcase_ = 'specialize:arg(1)'

def execute_varargs(cpu, opnum, argboxes, descr):
    # only for opnums with a variable arity (calls, typically)
    check_descr(descr)
    func = get_execute_function(cpu, opnum, -1)
    assert func is not None
    return func(cpu, argboxes, descr)
execute_varargs._annspecialcase_ = 'specialize:arg(1)'


def execute_nonspec(cpu, opnum, argboxes, descr=None):
    arity = resoperation.oparity[opnum]
    assert arity == -1 or len(argboxes) == arity
    if resoperation.opwithdescr[opnum]:
        check_descr(descr)
        if arity == -1:
            func = get_execute_funclist(cpu, -1)[opnum]
            return func(cpu, argboxes, descr)
        if arity == 0:
            func = get_execute_funclist(cpu, 1)[opnum]
            return func(cpu, descr)
        if arity == 1:
            func = get_execute_funclist(cpu, 2)[opnum]
            return func(cpu, argboxes[0], descr)
        if arity == 2:
            func = get_execute_funclist(cpu, 3)[opnum]
            return func(cpu, argboxes[0], argboxes[1], descr)
        if arity == 3:
            func = get_execute_funclist(cpu, 4)[opnum]
            return func(cpu, argboxes[0], argboxes[1], argboxes[2], descr)
    else:
        assert descr is None
        if arity == 1:
            func = get_execute_funclist(cpu, 1)[opnum]
            return func(cpu, argboxes[0])
        if arity == 2:
            func = get_execute_funclist(cpu, 2)[opnum]
            return func(cpu, argboxes[0], argboxes[1])
        if arity == 3:
            func = get_execute_funclist(cpu, 3)[opnum]
            return func(cpu, argboxes[0], argboxes[1], argboxes[2])
    raise NotImplementedError
