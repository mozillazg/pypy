"""This implements pyjitpl's execution of operations.
"""

import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.rarithmetic import ovfcheck, r_uint, intmask
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp.history import BoxInt, BoxPtr, BoxFloat, check_descr
from pypy.jit.metainterp.history import INT, REF, FLOAT
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.blackhole import BlackholeInterpreter, NULL

# ____________________________________________________________

def do_call(cpu, argboxes, descr):
    # count the number of arguments of the different types
    count_i = count_r = count_f = 0
    for i in range(1, len(argboxes)):
        type = argboxes[i].type
        if   type == INT:   count_i += 1
        elif type == REF:   count_r += 1
        elif type == FLOAT: count_f += 1
    # allocate lists for each type that has at least one argument
    if count_i: args_i = [0] * count_i
    else:       args_i = None
    if count_r: args_r = [NULL] * count_r
    else:       args_r = None
    if count_f: args_f = [0.0] * count_f
    else:       args_f = None
    # fill in the lists
    count_i = count_r = count_f = 0
    for i in range(1, len(argboxes)):
        box = argboxes[i]
        if   box.type == INT:
            args_i[count_i] = box.getint()
            count_i += 1
        elif box.type == REF:
            args_r[count_r] = box.getref_base()
            count_r += 1
        elif box.type == FLOAT:
            args_f[count_f] = box.getfloat()
            count_f += 1
    # get the function address as an integer
    func = argboxes[0].getint()
    # do the call using the correct function from the cpu
    rettype = descr.get_return_type()
    if rettype == INT:
        result = cpu.bh_call_i(func, descr, args_i, args_r, args_f)
        return BoxInt(result)
    if rettype == REF:
        result = cpu.bh_call_r(func, descr, args_i, args_r, args_f)
        return BoxPtr(result)
    if rettype == FLOAT:
        result = cpu.bh_call_f(func, descr, args_i, args_r, args_f)
        return BoxFloat(result)
    if rettype == 'v':   # void
        cpu.bh_call_v(func, descr, args_i, args_r, args_f)
        return None
    raise AssertionError("bad rettype")

def do_setarrayitem_gc(cpu, arraybox, indexbox, itembox, arraydescr):
    array = arraybox.getref_base()
    index = indexbox.getint()
    if itembox.type == INT:
        item = itembox.getint()
        cpu.bh_setarrayitem_gc_i(arraydescr, array, index, item)
    elif itembox.type == REF:
        item = itembox.getref_base()
        cpu.bh_setarrayitem_gc_r(arraydescr, array, index, item)
    elif itembox.type == FLOAT:
        item = itembox.getfloat()
        cpu.bh_setarrayitem_gc_f(arraydescr, array, index, item)
    else:
        raise AssertionError("bad itembox.type")

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
            #
            # Fish for a way for the pyjitpl interpreter to delegate
            # really running the operation to the blackhole interpreter
            # or directly to the cpu.  First try the do_xxx() functions
            # explicitly encoded above:
            name = 'do_' + key.lower()
            if name in globals():
                execute[value] = globals()[name]
                continue
            # If missing, fallback to the bhimpl_xxx() method of the
            # blackhole interpreter.  This only works if there is a
            # method of the exact same name and it accepts simple
            # parameters.
            name = 'bhimpl_' + key.lower()
            if hasattr(BlackholeInterpreter, name):
                func = make_execute_function_with_boxes(
                    key.lower(),
                    getattr(BlackholeInterpreter, name).im_func)
                if func is not None:
                    execute[value] = func
                    continue
            print "XXX warning: missing", key
    cpuclass._execute_by_num_args = execute_by_num_args

def make_execute_function_with_boxes(name, func):
    # Make a wrapper for 'func'.  The func is a simple bhimpl_xxx function
    # from the BlackholeInterpreter class.  The wrapper is a new function
    # that receives and returns boxed values.
    for argtype in func.argtypes:
        if argtype not in ('i', 'r', 'f', 'd', 'cpu'):
            return None
    if func.resulttype not in ('i', 'r', 'f', None):
        return None
    argtypes = unrolling_iterable(func.argtypes)
    resulttype = func.resulttype
    #
    def do(cpu, *argboxes):
        newargs = ()
        for argtype in argtypes:
            if argtype == 'cpu':
                value = cpu
            elif argtype == 'd':
                value = argboxes[-1]
                argboxes = argboxes[:-1]
            else:
                argbox = argboxes[0]
                argboxes = argboxes[1:]
                if argtype == 'i':   value = argbox.getint()
                elif argtype == 'r': value = argbox.getref_base()
                elif argtype == 'f': value = argbox.getfloat()
            newargs = newargs + (value,)
        assert not argboxes
        #
        result = func(*newargs)
        #
        if resulttype == 'i': return BoxInt(result)
        if resulttype == 'r': return BoxPtr(result)
        if resulttype == 'f': return BoxFloat(result)
        return None
    #
    do.func_name = 'do_' + name
    return do

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
    return func(cpu, *argboxes)     # note that the 'argboxes' tuple
                                    # optionally ends with the descr
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
