"""
This file defines utilities for manipulating the stack in an
RPython-compliant way, intended mostly for use by the Stackless PyPy.
"""
import py
import inspect, random, sys, dis

def stack_unwind():
    raise RuntimeError("cannot unwind stack in non-translated versions")

def stack_capture():
    raise RuntimeError("cannot unwind stack in non-translated versions")

def stack_frames_depth():
    return len(inspect.stack())

def stack_too_big():
    return False

def stack_check():
    if stack_too_big():
        # stack_unwind implementation is different depending on if stackless
        # is enabled. If it is it unwinds the stack, otherwise it simply
        # raises a RuntimeError.
        stack_unwind()

# ____________________________________________________________

def yield_current_frame_to_caller():
    raise NotImplementedError("only works in translated versions")

class frame_stack_top(object):
    def switch(self):
        raise NotImplementedError("only works in translated versions")


from pypy.rpython.extregistry import ExtRegistryEntry

def resume_point(name, *args, **kwargs):
    if not isinstance(name, str):
        raise TypeError("resume point name has to be a string")
    assert len(kwargs) <= 1
    #print "    resume_point", name
    resume_data = ResumeData.current_resume_data
    if resume_data is None or not resume_data.is_resuming(name):
        #print "     not resuming"
        return
    frame = sys._getframe(1)
    print "    ", frame, frame.f_locals
    setvals = {}
    assert len(resume_data.args) == len(args), (
            "resume state for %s created with wrong number of arguments" %
            (name, ))
    for name, val in frame.f_locals.iteritems():
        for i, arg in enumerate(args):
            if val is arg:
                if name in setvals:
                    raise ValueError(
                        "Could not reliably determine value of %s" % name)
                setvals[name] = val
                resume_data.set_local(name, resume_data.args[i], 1)
        if kwargs:
            if val is kwargs["returns"]:
                if resume_data.returning is NOTHING:
                    assert resume_data.raising is not NOTHING
                    continue
                if name in setvals:
                    raise ValueError(
                        "Could not reliably determine value of %s" % name)
                setvals[name] = val
                resume_data.set_local(name, resume_data.returning, 1)
    if resume_data.raising is not NOTHING:
        print "raising..."
        e = resume_data.raising
        resume_data.resuming_finished()
        raise e
    resume_data.resuming_finished()


class ResumePointFnEntry(ExtRegistryEntry):
    _about_ = resume_point

    def compute_result_annotation(self, s_label, *args_s, **kwds_s):
        from pypy.annotation import model as annmodel
        return annmodel.s_None

    def specialize_call(self, hop, **kwds_i):
        from pypy.rpython.lltypesystem import lltype
        from pypy.objspace.flow import model

        assert hop.args_s[0].is_constant()
        c_label = hop.inputconst(lltype.Void, hop.args_s[0].const)
        args_v = hop.args_v[1:]
        if 'i_returns' in kwds_i:
            assert len(kwds_i) == 1
            returns_index = kwds_i['i_returns']
            v_return = args_v.pop(returns_index-1)
            assert isinstance(v_return, model.Variable), \
                   "resume_point returns= argument must be a Variable"
        else:
            assert not kwds_i
            v_return = hop.inputconst(lltype.Void, None)

        for v in args_v:
            assert isinstance(v, model.Variable), "resume_point arguments must be Variables"

        hop.exception_is_here()
        return hop.genop('resume_point', [c_label, v_return] + args_v,
                         hop.r_result)

def resume_state_create(prevstate, label, func, *args):
    if label == "yield_current_frame_to_caller_1":
        assert func is None
        XXX
    return ResumeData(prevstate, label, func, *args)

def concretify_argument(hop, index):
    from pypy.objspace.flow import model

    v_arg = hop.args_v[index]
    if isinstance(v_arg, model.Variable):
        return v_arg

    r_arg = hop.rtyper.bindingrepr(v_arg)
    return hop.inputarg(r_arg, arg=index)

class ResumeStateCreateFnEntry(ExtRegistryEntry):
    _about_ = resume_state_create

    def compute_result_annotation(self, s_prevstate, s_label, s_ignore, *args_s):
        from pypy.annotation import model as annmodel
        return annmodel.SomeExternalObject(frame_stack_top)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        from pypy.rpython.rmodel import SimplePointerRepr
        from pypy.translator.stackless.frame import STATE_HEADER

        assert hop.args_s[1].is_constant()
        c_label = hop.inputconst(lltype.Void, hop.args_s[1].const)
        c_func = hop.inputconst(lltype.Void, hop.args_s[2].const)

        v_state = hop.inputarg(hop.r_result, arg=0)

        args_v = []
        for i in range(2, len(hop.args_v)):
            args_v.append(concretify_argument(hop, i))

        hop.exception_is_here()
        return hop.genop('resume_state_create', [v_state, c_label] + args_v,
                         hop.r_result)

def resume_state_invoke(type, state, **kwds):
    return state.resume(**kwds)

class ResumeStateInvokeFnEntry(ExtRegistryEntry):
    _about_ = resume_state_invoke

    def compute_result_annotation(self, s_type, s_state, **kwds):
        from pypy.annotation.bookkeeper import getbookkeeper
        assert s_type.is_constant()
        return getbookkeeper().valueoftype(s_type.const)

    def specialize_call(self, hop, **kwds_i):
        from pypy.rpython.lltypesystem import lltype
        v_state = hop.args_v[1]
        
        if 'i_returning' in kwds_i:
            assert len(kwds_i) == 1
            returning_index = kwds_i['i_returning']
            v_returning = concretify_argument(hop, returning_index)
            v_raising = hop.inputconst(lltype.Void, None)
        elif 'i_raising' in kwds_i:
            assert len(kwds_i) == 1
            raising_index = kwds_i['i_raising']
            v_returning = hop.inputconst(lltype.Void, None)
            v_raising = concretify_argument(hop, raising_index)
        else:
            assert not kwds_i
            v_returning = hop.inputconst(lltype.Void, None)
            v_raising = hop.inputconst(lltype.Void, None)

        hop.exception_is_here()
        return hop.genop('resume_state_invoke', [v_state, v_returning, v_raising],
                         hop.r_result)
        
        
# __________________________________________________________________
# the following code is used for the (quite hackish) implementation
# of resume states on top of CPython



operations = [
    ('operator.pos',         'pos',       1, ['__pos__']),
    ('operator.neg',         'neg',       1, ['__neg__']),
    ('abs',                  'abs',       1, ['__abs__']),
    ('operator.invert',      '~',         1, ['__invert__']),
    ('getattr',              'getattr',   2, ['__getattr__']),
    ('operator.getitem',     'getitem',   2, ['__getitem__']),
    ('operator.add',         '+',         2, ['__add__', '__radd__']),
    ('operator.sub',         '-',         2, ['__sub__', '__rsub__']),
    ('operator.mul',         '*',         2, ['__mul__', '__rmul__']),
    ('operator.truediv',     '/',         2, ['__truediv__', '__rtruediv__']),
    ('operator.floordiv',    '//',        2, ['__floordiv__', '__rfloordiv__']),
    ('operator.div',         'div',       2, ['__div__', '__rdiv__']),
    ('operator.mod',         '%',         2, ['__mod__', '__rmod__']),
    ('operator.divmod',      'divmod',    2, ['__divmod__', '__rdivmod__']),
    ('operator.lshift',      '<<',        2, ['__lshift__', '__rlshift__']),
    ('operator.rshift',      '>>',        2, ['__rshift__', '__rrshift__']),
    ('operator.and_',        '&',         2, ['__and__', '__rand__']),
    ('operator.or_',         '|',         2, ['__or__', '__ror__']),
    ('operator.xor',         '^',         2, ['__xor__', '__rxor__']),
    ('operator.lt',          '<',         2, ['__lt__', '__gt__']),
    ('operator.le',          '<=',        2, ['__le__', '__ge__']),
    ('operator.eq',          '==',        2, ['__eq__', '__eq__']),
    ('operator.ne',          '!=',        2, ['__ne__', '__ne__']),
    ('operator.gt',          '>',         2, ['__gt__', '__lt__']),
    ('operator.ge',          '>=',        2, ['__ge__', '__le__']),
    ('cmp',                  'cmp',       2, ['__cmp__']),
]

class Blackhole(object):
    for impl, _, arity, names in operations:
        args = ", ".join(["v%s" % i for i in range(arity)])
        for name in names:
            exec py.code.Source("""
    def %s(%s):
        return v0.__class__()
    """ % (name, args)).compile()

    def __pow__(self, *args):
        return self.__class__()

    def __call__(self, *args):
        return self.__class__()


class HomingBlackhole(Blackhole):
    def __nonzero__(self):
        print "taking decision",
        decision = ResumeData.current_resume_data.pop_next_decision("bool")[1]
        print decision
        return decision

    def next(self):
        print "taking decision"
        decision = ResumeData.current_resume_data.pop_next_decision("next")[1]
        print decision
        if decision == "stop":
            raise StopIteration
        return self.__class__()

    def __iter__(self):
        return self.__class__()

    def _freeze_(self):
        assert 0 # a HomingBlackhole was left!!!



NOTHING = object()

class ResumeData(object):
    current_resume_data = None

    def __init__(self, goto_after, name, func, *args):
        self.local_changes = []
        self.goto_after = goto_after
        self.name = name
        if isinstance(func, type(self.__init__)):
            func = func.im_func
        self.func = func
        self.args = args
        self.decision_stack = None
        self.likely_frame = None
        self.previous_globals = None
        self.returning = NOTHING
        self.raising = NOTHING

    def register_local_change(self, frame, name, value):
        assert frame is self.likely_frame
        self.local_changes.append((name, value))

    def pop_local_changes(self, frame):
        assert frame is self.likely_frame
        res = self.local_changes
        self.local_changes = []
        return res

    def is_resuming(self, name):
        return self.name == name

    def resume(self, returning=NOTHING, raising=NOTHING):
        assert returning is NOTHING or raising is NOTHING
        try:
            ResumeData.current_resume_data = self
            self.returning = returning
            self.raising = raising
            dummy_args = [HomingBlackhole()] * self.func.func_code.co_argcount
            paths, other_globals = find_path_to_resume_point(self.func)
            self.fix_globals = [g for g, val in other_globals.items() if val]
            decisions = paths[self.name][:]
            decisions.reverse()
            self.decision_stack = decisions
            sys.settrace(self.resume_tracer)
            try:
                result = self.func(*dummy_args)
            except Exception, e:
                if self.goto_after is not None:
                    print "caught %s, handing it on..." % (e, )
                    return self.goto_after.resume(raising=e)
                raise
        finally:
            sys.settrace(None)
        if self.goto_after is not None:
            return self.goto_after.resume(returning=result)
        return result

    def pop_next_decision(self, what):
        assert self.decision_stack[-1][0] == what
        return self.decision_stack.pop()

    def resuming_finished(self):
        self.decisions = None
        ResumeData.current_resume_data = None
        self.returning = NOTHING
        self.raising = NOTHING

    def possible_frame(self, frame):
        if self.likely_frame is None:
            self.likely_frame = frame
            return True
        return frame is self.likely_frame

    def set_local(self, local, val, levels=0):
        frame = sys._getframe(levels + 1)
        self.register_local_change(frame, local, val)

    def resume_tracer(self, frame, what, x):
        is_resume_frame = self.possible_frame(frame)
#        print frame, what, x, is_resume_frame
        if not is_resume_frame:
            return None
        # still waiting for resume_point?
        if ResumeData.current_resume_data is self:
            newlocals = {}
            for name, val in frame.f_locals.iteritems():
                if not isinstance(val, HomingBlackhole):
                    val = HomingBlackhole()
                    newlocals[name] = val
            if newlocals:
                print "fixing locals", newlocals
                frame.f_locals.update(newlocals)
            if self.fix_globals:
                self.previous_globals = {}
                print "fixing globals", self.fix_globals
                for gl in self.fix_globals:
                    try:
                        oldvalue = frame.f_globals[gl]
                    except KeyError:
                        oldvalue = NOTHING
                    frame.f_globals[gl] = HomingBlackhole()
                    self.previous_globals[gl] = oldvalue
                    assert gl in frame.f_globals
                self.fix_globals = None
        else:
            print "restore correct globals"
            if self.previous_globals is not None:
                for gl, oldvalue in self.previous_globals.iteritems():
                    if oldvalue is NOTHING:
                        if gl in frame.f_globals:
                            del frame.f_globals[gl]
                    else:
                        frame.f_globals[gl] = oldvalue
        changes = self.pop_local_changes(frame)
        if changes:
            print 'changes', dict(changes), changes
            frame.f_locals.update(dict(changes))
        return self.resume_tracer

    def switch(self):
        return self.resume()


# _________________________________________________________________________
# Functions to analyze bytecode to find a way to reach resume_points

def find_basic_blocks(code):
    labels = []
    n = len(code)
    i = 0
    while i < n:
        c = code[i]
        op = ord(c)
        i = i + 1
        if op >= dis.HAVE_ARGUMENT:
            oparg = ord(code[i]) + ord(code[i+1])*256
            i = i+2
            label = -1
            if op in dis.hasjrel:
                label = i+oparg
            elif op in dis.hasjabs:
                label = oparg
            if label >= 0:
                if label not in labels:
                    labels.append(label)
                if i - 3 not in labels:
                    labels.append(i - 3)
    return labels

def split_opcode_args(code):
    ops_args = []
    n = len(code)
    i = 0
    while i < n:
        c = code[i]
        op = ord(c)
        i = i + 1
        if op >= dis.HAVE_ARGUMENT:
            oparg = ord(code[i]) + ord(code[i+1])*256
            ops_args.append((i - 1, dis.opname[op], oparg))
            i = i+2
        else:
            ops_args.append((i - 1, dis.opname[op], None))
    return ops_args

def find_resume_points_and_other_globals(func):
    code_obj = func.func_code
    code = code_obj.co_code
    ops_args = split_opcode_args(code)
    globals = func.func_globals
    loaded_global = None
    loaded_global_name = None
    positions = []
    other_globals = {}
    for i, (pos, opname, arg) in enumerate(ops_args):
        resume_pos = -1
        if opname == "LOAD_GLOBAL":
            loaded_global_name = code_obj.co_names[arg]
            try:
                loaded_global = globals[loaded_global_name]
            except KeyError:
                loaded_global = None
            if loaded_global is resume_point:
                resume_pos = pos
                loaded_global = None
                other_globals[loaded_global_name] = False
            else:
                if (loaded_global_name not in other_globals and 
                    loaded_global_name is not None):
                    other_globals[loaded_global_name] = True
        elif opname == "LOAD_ATTR":
            if getattr(loaded_global,
                       code_obj.co_names[arg], None) is resume_point:
                resume_pos = pos
                loaded_global = None
                other_globals[loaded_global_name] = False
            else:
                if (loaded_global_name not in other_globals and 
                    loaded_global_name is not None):
                    other_globals[loaded_global_name] = True
        else:
            loaded_global = None
        if resume_pos >= 0:
            if i + 1 >= len(ops_args) or ops_args[i + 1][1] != "LOAD_CONST":
                raise TypeError(
                    "could not statically determine resume point names")
            else:
                positions.append((pos, code_obj.co_consts[ops_args[i + 1][2]]))
    if len(dict.fromkeys(positions)) != len(positions):
        raise TypeError("duplicate resume point name")
    return positions, other_globals

def _get_targets_with_condition(pos, name, arg):
    op = dis.opname.index(name)
    if op in dis.hasjrel:
        target = pos + arg + 3
        if name == "JUMP_IF_FALSE":
            return [(target, "bool", False), (pos + 3, "bool", True)]
        elif name == "JUMP_IF_TRUE":
            return [(target, "bool", True), (pos + 3, "bool", False)]
        elif name == "JUMP_FORWARD":
            return [(target, None, None)]
        elif name in ("SETUP_LOOP", "SETUP_FINALLY", "SETUP_EXCEPT"):
            return [(pos + 3, None, None)] #XXX not sure
        elif name == "FOR_ITER":
            return [(target, "next", "stop")]
        assert 0, "not implemented"
    elif op in dis.hasjabs:
        if name == "JUMP_ABSOLUTE":
            return [(arg, None, None)]
        assert 0, "not implemented"
    else:
        if op > dis.HAVE_ARGUMENT:
            return [(pos + 3, None, None)]
        else:
            return [(pos + 1, None, None)]
        assert 0, "not implemented"

def find_path_to_resume_point(func):
    resume_points, other_globals = find_resume_points_and_other_globals(func)
    ops_args = split_opcode_args(func.func_code.co_code)
    paths = {ops_args[0][0]: []}
    last_unknown = None
    while 1:
        flip_boolean = False
        num_nots = 0
        unknown = {}
        for i, (pos, name, arg) in enumerate(ops_args):
            path = paths.get(pos, None)
            if path is None:
                unknown[path] = True
                continue
            targets = _get_targets_with_condition(pos, name, arg)
            if name == "UNARY_NOT":
                flip_boolean = not flip_boolean
                num_nots += 1
            elif num_nots:
                num_nots = 0
                for i in range(len(targets)):
                    target, what, value = targets[i]
                    if what is None:
                        flip_boolean = False
                        targets[i] = target, "bool", False
            for target, what, value in targets:
                oldpath = paths.get(target, None)
                if oldpath is None or len(oldpath) > len(path) + 1:
                    if what == "bool" and flip_boolean:
                        value = not value
                    paths[target] = path + [(what, value)]
        if not unknown or unknown == last_unknown:
            break
        last_unknown = unknown
    result = {}
    for pos, name in resume_points:
        if pos in paths:
            result[name] = [(how, what) for how, what in paths[pos]
                                            if how is not None]
    return result, other_globals
