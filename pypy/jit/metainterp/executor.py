"""This implements pyjitpl's execution of operations.
"""

from pypy.rpython.lltypesystem import lltype, rstr
from pypy.rlib.rarithmetic import ovfcheck, r_longlong, is_valid_int
from pypy.rlib.rtimer import read_timestamp
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp.history import check_descr, AbstractDescr
from pypy.jit.metainterp.resoperation import INT, REF, FLOAT, rop,\
     create_resop, create_resop_1, create_resop_2, create_resop_0
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.blackhole import BlackholeInterpreter, NULL
from pypy.jit.codewriter import longlong

# ____________________________________________________________

def new_do_call(opnum, tp):
    def do_call(cpu, metainterp, argboxes, descr):
        assert metainterp is not None
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
        if count_f: args_f = [longlong.ZEROF] * count_f
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
                args_f[count_f] = box.getfloatstorage()
                count_f += 1
        # get the function address as an integer
        func = argboxes[0].getint()
        # do the call using the correct function from the cpu
        if tp == 'i':
            try:
                result = cpu.bh_call_i(func, args_i, args_r, args_f, descr)
            except Exception, e:
                metainterp.execute_raised(e)
                result = 0
            return create_resop(opnum, result, argboxes, descr)
        if tp == 'p':
            try:
                result = cpu.bh_call_r(func, args_i, args_r, args_f, descr)
            except Exception, e:
                metainterp.execute_raised(e)
                result = NULL
            return create_resop(opnum, result, argboxes, descr)
        if tp == 'f':
            try:
                result = cpu.bh_call_f(func, args_i, args_r, args_f, descr)
            except Exception, e:
                metainterp.execute_raised(e)
                result = longlong.ZEROF
            return create_resop(opnum, result, argboxes, descr)
        if tp == 'N':
            try:
                cpu.bh_call_v(func, args_i, args_r, args_f, descr)
            except Exception, e:
                metainterp.execute_raised(e)
            return create_resop(opnum, None, argboxes, descr)
        raise AssertionError("bad rettype")
    return do_call

do_call_i = new_do_call(rop.CALL_i, 'i')
do_call_f = new_do_call(rop.CALL_f, 'f')
do_call_r = new_do_call(rop.CALL_r, 'r')
do_call_v = new_do_call(rop.CALL_v, 'v')
do_call_loopinvariant_i = new_do_call(rop.CALL_LOOPINVARIANT_i, 'i')
do_call_loopinvariant_f = new_do_call(rop.CALL_LOOPINVARIANT_f, 'f')
do_call_loopinvariant_r = new_do_call(rop.CALL_LOOPINVARIANT_r, 'r')
do_call_loopinvariant_v = new_do_call(rop.CALL_LOOPINVARIANT_v, 'v')
do_call_may_force_i = new_do_call(rop.CALL_MAY_FORCE_i, 'i')
do_call_may_force_f = new_do_call(rop.CALL_MAY_FORCE_f, 'f')
do_call_may_force_r = new_do_call(rop.CALL_MAY_FORCE_r, 'r')
do_call_may_force_v = new_do_call(rop.CALL_MAY_FORCE_v, 'v')
do_call_pure_i = new_do_call(rop.CALL_PURE_i, 'i')
do_call_pure_f = new_do_call(rop.CALL_PURE_f, 'f')
do_call_pure_r = new_do_call(rop.CALL_PURE_r, 'r')
do_call_pure_v = new_do_call(rop.CALL_PURE_v, 'v')

def do_setarrayitem_gc(cpu, _, arraybox, indexbox, itembox, arraydescr):
    array = arraybox.getref_base()
    index = indexbox.getint()
    if arraydescr.is_array_of_pointers():
        cpu.bh_setarrayitem_gc_r(array, index,
                                 itembox.getref_base(), arraydescr)
    elif arraydescr.is_array_of_floats():
        cpu.bh_setarrayitem_gc_f(array, index,
                                 itembox.getfloatstorage(), arraydescr)
    else:
        cpu.bh_setarrayitem_gc_i(array, index, itembox.getint(), arraydescr)

def do_setarrayitem_raw(cpu, _, arraybox, indexbox, itembox, arraydescr):
    array = arraybox.getint()
    index = indexbox.getint()
    assert not arraydescr.is_array_of_pointers()
    if arraydescr.is_array_of_floats():
        cpu.bh_setarrayitem_raw_f(array, index,
                                  itembox.getfloatstorage(), arraydescr)
    else:
        cpu.bh_setarrayitem_raw_i(array, index, itembox.getint(), arraydescr)

def do_setinteriorfield_gc(cpu, _, arraybox, indexbox, valuebox, descr):
    array = arraybox.getref_base()
    index = indexbox.getint()
    if descr.is_pointer_field():
        cpu.bh_setinteriorfield_gc_r(array, index,
                                     valuebox.getref_base(), descr)
    elif descr.is_float_field():
        cpu.bh_setinteriorfield_gc_f(array, index,
                                     valuebox.getfloatstorage(), descr)
    else:
        cpu.bh_setinteriorfield_gc_i(array, index,
                                     valuebox.getint(), descr)

def do_setfield_gc(cpu, _, structbox, itembox, fielddescr):
    struct = structbox.getref_base()
    if fielddescr.is_pointer_field():
        cpu.bh_setfield_gc_r(struct, itembox.getref_base(), fielddescr)
    elif fielddescr.is_float_field():
        cpu.bh_setfield_gc_f(struct, itembox.getfloatstorage(), fielddescr)
    else:
        cpu.bh_setfield_gc_i(struct, itembox.getint(), fielddescr)

def do_setfield_raw(cpu, _, structbox, itembox, fielddescr):
    struct = structbox.getint()
    if fielddescr.is_pointer_field():
        cpu.bh_setfield_raw_r(struct, itembox.getref_base(), fielddescr)
    elif fielddescr.is_float_field():
        cpu.bh_setfield_raw_f(struct, itembox.getfloatstorage(), fielddescr)
    else:
        cpu.bh_setfield_raw_i(struct, itembox.getint(), fielddescr)

def do_raw_store(cpu, _, addrbox, offsetbox, valuebox, arraydescr):
    addr = addrbox.getint()
    offset = offsetbox.getint()
    if arraydescr.is_array_of_pointers():
        raise AssertionError("cannot store GC pointers in raw store")
    elif arraydescr.is_array_of_floats():
        cpu.bh_raw_store_f(addr, offset, valuebox.getfloatstorage(),
                           arraydescr)
    else:
        cpu.bh_raw_store_i(addr, offset, valuebox.getint(), arraydescr)

def do_raw_load_r(cpu, _, addrbox, offsetbox, arraydescr):
    raise AssertionError("cannot store GC pointers in raw store")

def do_raw_load_i(cpu, _, addrbox, offsetbox, arraydescr):
    addr = addrbox.getint()
    offset = offsetbox.getint()
    res = cpu.bh_raw_load_i(addr, offset, arraydescr) 
    return create_resop_2(rop.RAW_LOAD_i, res, addrbox, offsetbox,
                          descr=arraydescr)

def do_raw_load_f(cpu, _, addrbox, offsetbox, arraydescr):
    addr = addrbox.getint()
    offset = offsetbox.getint()
    res = cpu.bh_raw_load_f(addr, offset, arraydescr)
    return create_resop_2(rop.RAW_LOAD_f, res, addrbox, offsetbox,
                          descr=arraydescr)

def exec_new_with_vtable(cpu, clsbox):
    from pypy.jit.codewriter import heaptracker
    vtable = clsbox.getint()
    descr = heaptracker.vtable2descr(cpu, vtable)
    return cpu.bh_new_with_vtable(vtable, descr)

def do_new_with_vtable(cpu, _, clsbox):
    pval = exec_new_with_vtable(cpu, clsbox)
    return create_resop_1(rop.NEW_WITH_VTABLE, pval, clsbox)

def do_int_add_ovf(cpu, metainterp, box1, box2):
    # the overflow operations can be called without a metainterp, if an
    # overflow cannot occur
    a = box1.getint()
    b = box2.getint()
    try:
        z = ovfcheck(a + b)
    except OverflowError:
        assert metainterp is not None
        metainterp.execute_raised(OverflowError(), constant=True)
        z = 0
    return create_resop_2(rop.INT_ADD_OVF, z, box1, box2)

def do_int_sub_ovf(cpu, metainterp, box1, box2):
    a = box1.getint()
    b = box2.getint()
    try:
        z = ovfcheck(a - b)
    except OverflowError:
        assert metainterp is not None
        metainterp.execute_raised(OverflowError(), constant=True)
        z = 0
    return create_resop_2(rop.INT_SUB_OVF, z, box1, box2)

def do_int_mul_ovf(cpu, metainterp, box1, box2):
    a = box1.getint()
    b = box2.getint()
    try:
        z = ovfcheck(a * b)
    except OverflowError:
        assert metainterp is not None
        metainterp.execute_raised(OverflowError(), constant=True)
        z = 0
    return create_resop_2(rop.INT_MUL_OVF, z, box1, box2)

def do_same_as_i(cpu, _, box):
    return box.nonconstbox()
do_same_as_f = do_same_as_i
do_same_as_r = do_same_as_i

def do_copystrcontent(cpu, _, srcbox, dstbox,
                      srcstartbox, dststartbox, lengthbox):
    src = srcbox.getref(lltype.Ptr(rstr.STR))
    dst = dstbox.getref(lltype.Ptr(rstr.STR))
    srcstart = srcstartbox.getint()
    dststart = dststartbox.getint()
    length = lengthbox.getint()
    rstr.copy_string_contents(src, dst, srcstart, dststart, length)

def do_copyunicodecontent(cpu, _, srcbox, dstbox,
                          srcstartbox, dststartbox, lengthbox):
    src = srcbox.getref(lltype.Ptr(rstr.UNICODE))
    dst = dstbox.getref(lltype.Ptr(rstr.UNICODE))
    srcstart = srcstartbox.getint()
    dststart = dststartbox.getint()
    length = lengthbox.getint()
    rstr.copy_unicode_contents(src, dst, srcstart, dststart, length)

def do_read_timestamp(cpu, _):
    x = read_timestamp()
    if longlong.is_64_bit:
        assert is_valid_int(x)            # 64-bit
    else:
        assert isinstance(x, r_longlong)  # 32-bit
    return create_resop_0(rop.READ_TIMESTAMP, x)

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


def _make_execute_list():
    execute_by_num_args = {}
    for key, value in rop.__dict__.items():
        orig_key = key
        if not key.startswith('_'):
            if (rop._FINAL_FIRST <= value <= rop._FINAL_LAST or
                rop._GUARD_FIRST <= value <= rop._GUARD_LAST):
                continue
            # find which list to store the operation in, based on num_args
            num_args = resoperation.oparity[value]
            withdescr = resoperation.opwithdescr[value]
            dictkey = num_args, withdescr
            if dictkey not in execute_by_num_args:
                execute_by_num_args[dictkey] = [None] * (rop._LAST+1)
            execute = execute_by_num_args[dictkey]
            #
            if execute[value] is not None:
                raise AssertionError("duplicate entry for op number %d"% value)
            #
            # Fish for a way for the pyjitpl interpreter to delegate
            # really running the operation to the blackhole interpreter
            # or directly to the cpu.  First try the do_xxx() functions
            # explicitly encoded above:
            name = 'do_' + key.lower()
            if name in globals():
                execute[value] = globals()[name]
                continue
            #
            # Maybe the same without the _PURE suffix?
            if key[-7:-2] == '_PURE':
                key = key[:-7] + key[-2:]
                name = 'do_' + key.lower()
                if name in globals():
                    execute[value] = globals()[name]
                    continue
            #
            # If missing, fallback to the bhimpl_xxx() method of the
            # blackhole interpreter.  This only works if there is a
            # method of the exact same name and it accepts simple
            # parameters.
            name = 'bhimpl_' + key.lower()
            if hasattr(BlackholeInterpreter, name):
                func = make_execute_function_with_boxes(
                    value,
                    key.lower(),
                    getattr(BlackholeInterpreter, name).im_func)
                if func is not None:
                    execute[value] = func
                    continue
            if value in (rop.JIT_FRAME,
                         rop.CALL_ASSEMBLER,
                         rop.COND_CALL_GC_WB,
                         rop.COND_CALL_GC_WB_ARRAY,
                         rop.DEBUG_MERGE_POINT,
                         rop.JIT_DEBUG,
                         rop.SETARRAYITEM_RAW,
                         rop.GETINTERIORFIELD_RAW_i,
                         rop.GETINTERIORFIELD_RAW_f,
                         rop.SETINTERIORFIELD_RAW,
                         rop.CALL_RELEASE_GIL_i,
                         rop.CALL_RELEASE_GIL_r,
                         rop.CALL_RELEASE_GIL_f,
                         rop.CALL_RELEASE_GIL_v,
                         rop.QUASIIMMUT_FIELD,
                         rop.CALL_MALLOC_GC,
                         rop.CALL_MALLOC_NURSERY,
                         rop.LABEL,
                         rop.INPUT_i, rop.INPUT_r, rop.INPUT_f,
                         rop.FORCE_SPILL, rop.ESCAPE, rop.ESCAPE_r,
                         rop.ESCAPE_f,
                         ):      # list of opcodes never executed by pyjitpl
                continue
            raise AssertionError("missing %r" % (orig_key,))
    return execute_by_num_args

def make_execute_function_with_boxes(opnum, name, func):
    # Make a wrapper for 'func'.  The func is a simple bhimpl_xxx function
    # from the BlackholeInterpreter class.  The wrapper is a new function
    # that receives and returns boxed values.
    for i, argtype in enumerate(func.argtypes):
        if argtype not in ('i', 'r', 'f', 'd', 'cpu'):
            return None
        if argtype == 'd':
            if i != len(func.argtypes) - 1:
                raise AssertionError("Descr should be the last one")
    if list(func.argtypes).count('d') > 1:
        return None
    if func.resulttype not in ('i', 'r', 'f', None):
        return None
    argtypes = unrolling_iterable(func.argtypes)
    # count the actual arguments
    real_args = 0
    for argtype in func.argtypes:
        if argtype in ('i', 'r', 'f'):
            real_args += 1
    if real_args <= 3:
        create_resop_func = getattr(resoperation,
                                    'create_resop_%d' % real_args)
    #
        def do(cpu, _, *args):
            newargs = ()
            orig_args = args
            for argtype in argtypes:
                if argtype == 'cpu':
                    value = cpu
                elif argtype == 'd':
                    value = args[-1]
                    assert isinstance(value, AbstractDescr)
                    args = args[:-1]
                else:
                    arg = args[0]
                    args = args[1:]
                    if argtype == 'i':   value = arg.getint()
                    elif argtype == 'r': value = arg.getref_base()
                    elif argtype == 'f': value = arg.getfloatstorage()
                newargs = newargs + (value,)
            assert not args
            #
            result = func(*newargs)
            return create_resop_func(opnum, result, *orig_args)
            #
        #
    else:
        return None # it's only jitdebug, deal with it by hand
    do.func_name = 'do_' + name
    return do

def get_execute_funclist(num_args, withdescr):
    # workaround, similar to the next one
    return EXECUTE_BY_NUM_ARGS[num_args, withdescr]
get_execute_funclist._annspecialcase_ = 'specialize:memo'

def get_execute_function(opnum, num_args, withdescr):
    # workaround for an annotation limitation: putting this code in
    # a specialize:memo function makes sure the following line is
    # constant-folded away.  Only works if opnum and num_args are
    # constants, of course.
    func = EXECUTE_BY_NUM_ARGS[num_args, withdescr][opnum]
    assert func is not None, "EXECUTE_BY_NUM_ARGS[%s, %s][%s]" % (
        num_args, withdescr, resoperation.opname[opnum])
    return func
get_execute_function._annspecialcase_ = 'specialize:memo'

def has_descr(opnum):
    # workaround, similar to the previous one
    return resoperation.opwithdescr[opnum]
has_descr._annspecialcase_ = 'specialize:memo'


def execute(cpu, metainterp, opnum, descr, *args):
    # only for opnums with a fixed arity
    num_args = len(args)
    withdescr = has_descr(opnum)
    if withdescr:
        check_descr(descr)
        args = args + (descr,)
    else:
        assert descr is None
    func = get_execute_function(opnum, num_args, withdescr)
    return func(cpu, metainterp, *args)  # note that the 'args' tuple
                                         # optionally ends with the descr
execute._annspecialcase_ = 'specialize:arg(2)'

def execute_varargs(cpu, metainterp, opnum, argboxes, descr):
    # only for opnums with a variable arity (calls, typically)
    check_descr(descr)
    func = get_execute_function(opnum, -1, True)
    return func(cpu, metainterp, argboxes, descr)
execute_varargs._annspecialcase_ = 'specialize:arg(2)'


def execute_nonspec(cpu, metainterp, opnum, argboxes, descr=None):
    arity = resoperation.oparity[opnum]
    assert arity == -1 or len(argboxes) == arity
    if resoperation.opwithdescr[opnum]:
        check_descr(descr)
        if arity == -1:
            func = get_execute_funclist(-1, True)[opnum]
            return func(cpu, metainterp, argboxes, descr)
        if arity == 0:
            func = get_execute_funclist(0, True)[opnum]
            return func(cpu, metainterp, descr)
        if arity == 1:
            func = get_execute_funclist(1, True)[opnum]
            return func(cpu, metainterp, argboxes[0], descr)
        if arity == 2:
            func = get_execute_funclist(2, True)[opnum]
            return func(cpu, metainterp, argboxes[0], argboxes[1], descr)
        if arity == 3:
            func = get_execute_funclist(3, True)[opnum]
            return func(cpu, metainterp, argboxes[0], argboxes[1], argboxes[2],
                        descr)
    else:
        assert descr is None
        if arity == 1:
            func = get_execute_funclist(1, False)[opnum]
            return func(cpu, metainterp, argboxes[0])
        if arity == 2:
            func = get_execute_funclist(2, False)[opnum]
            return func(cpu, metainterp, argboxes[0], argboxes[1])
        if arity == 3:
            func = get_execute_funclist(3, False)[opnum]
            return func(cpu, metainterp, argboxes[0], argboxes[1], argboxes[2])
        if arity == 5:    # copystrcontent, copyunicodecontent
            func = get_execute_funclist(5, False)[opnum]
            return func(cpu, metainterp, argboxes[0], argboxes[1],
                        argboxes[2], argboxes[3], argboxes[4])
    raise NotImplementedError


EXECUTE_BY_NUM_ARGS = _make_execute_list()
