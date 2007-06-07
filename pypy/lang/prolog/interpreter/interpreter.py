from pypy.lang.prolog.interpreter import helper
from pypy.lang.prolog.interpreter import error
from pypy.lang.prolog.interpreter.term import Term, Atom, Var, Callable, \
    LocalVar
from pypy.lang.prolog.interpreter.engine import Continuation, \
    LimitedScopeContinuation, DONOTHING
from pypy.lang.prolog.interpreter.prologopcode import unrolling_opcode_descs, \
    HAVE_ARGUMENT

class FrameContinuation(Continuation):
    def __init__(self, frame, pc, continuation):
        self.frame = frame
        self.pc = pc
        self.continuation = continuation

    def _call(self, engine):
        return self.frame.run(self.frame.code.opcode, self.pc,
                              self.continuation)

class Rule(object):
    _immutable_ = True
    def __init__(self, head, body, engine):
        from pypy.lang.prolog.interpreter.compiler import compile
        head = helper.ensure_callable(head)
        self.head = head
        self.code = compile(head, body, engine)
        if body is not None:
            body = helper.ensure_callable(body)
            self.body = body
        else:
            self.body = None
        self.signature = self.head.signature
        self.engine = engine

    def make_frame(self, head):
        f = Frame(self.engine, self.code)
        f.unify_head(head)
        return f

    def __repr__(self):
        if self.body is None:
            return "%s." % (self.head, )
        return "%s :- %s." % (self.head, self.body)

class Query(object):
    def __init__(self, body, engine):
        from pypy.lang.prolog.interpreter.compiler import compile_query
        self.code = compile_query(body, engine)
        self.engine = engine

    def make_frame(self):
        return Frame(self.engine, self.code)


def dynamic_call_frame(engine, query):
    from pypy.lang.prolog.interpreter.compiler import Code
    frame = Frame(engine, Code.dynamic_code)
    frame.localvarcache[0] = query
    return frame


class Frame(object):
    #_immutable_ = True # XXX?

    def __init__(self, engine, code):
        self.engine = engine
        self.code = code
        self.localvarcache = [None] * code.maxlocalvar
        self.stack = None

    def unify_head(self, head):
        self.run(self.code.opcode_head, 0, None)
        self.stack[0].unify(head, self.engine.heap)
        self.stack = None

    def run_directly(self, continuation, choice_point=True):
        if self.code.opcode:
            continuation = self.run(self.code.opcode, 0, continuation)
        if not choice_point:
            return continuation
        while continuation is not DONOTHING:
            continuation = continuation._call(self.engine)
        return DONOTHING

    def run(self, bytecode, pc, continuation):
        stack = []
        while pc < len(bytecode):
            opcode = ord(bytecode[pc])
            pc += 1
            if opcode >= HAVE_ARGUMENT:
                hi = ord(bytecode[pc])
                lo = ord(bytecode[pc+1])
                pc += 2
                oparg = (hi << 8) | lo
            else:
                oparg = 0
            #import pdb; pdb.set_trace()
            for opdesc in unrolling_opcode_descs:
                if opcode == opdesc.index:
                    # dispatch to the opcode method
                    meth = getattr(self, opdesc.name)
                    if opdesc.hascontinuation:
                        cont = FrameContinuation(self, pc, continuation)
                        if opdesc.hasargument:
                            res = meth(stack, oparg, cont)
                        else:
                            res = meth(stack, cont)
                    else:
                        if opdesc.hasargument:
                            res = meth(stack, oparg)
                        else:
                            res = meth(stack)
                    if res is not None:
                        continuation = res
                        while continuation is not DONOTHING:
                            if isinstance(continuation, FrameContinuation):
                                self = continuation.frame
                                pc = continuation.pc
                                bytecode = self.code.opcode
                                continuation = continuation.continuation
                                stack = []
                                break
                            else:
                                print continuation
                                continuation = continuation._call(self.engine)
                    break
            else:
                assert 0, "missing opcode"
        if len(stack) != 0:
            self.stack = stack
        return continuation

    def PUTCONSTANT(self, stack, number):
        stack.append(self.code.constants[number])

    def MAKELOCALVAR(self, stack, number):
        result = self.localvarcache[number] = LocalVar()
        stack.append(result)

    def PUTLOCALVAR(self, stack, number):
        result = self.localvarcache[number]
        assert result is not None
        stack.append(result)

    def ACTIVATE_LOCAL(self, stack, number):
        var = self.localvarcache[number]
        if isinstance(var, LocalVar):
            self.localvarcache[number] = var.dereference(self.engine.heap)
            var.active = True

    def MAKETERM(self, stack, number):
        name, numargs, signature = self.code.term_info[number]
        args = [None] * numargs
        i = numargs - 1
        while i >= 0:
            args[i] = stack.pop()
            i -= 1
        stack.append(Term(name, args, signature))

    def CALL_BUILTIN(self, stack, number, continuation):
        from pypy.lang.prolog.builtin import builtins_list
        return builtins_list[number][1].call(self.engine, stack.pop(),
                                             continuation)

    def CUT(self, stack, continuation):
        raise error.CutException(continuation)
    
    def STATIC_CALL(self, stack, number, continuation):
        query = stack.pop()
        function = self.code.functions[number]
        return self.user_call(function, query, continuation)

    def DYNAMIC_CALL(self, stack, continuation):
        query = stack.pop()
        assert isinstance(query, Callable)
        signature = query.signature
        from pypy.lang.prolog.builtin import builtins
        if signature in builtins:
            builtin = builtins[signature]
            return builtin.call(self.engine, query, continuation)
        function = self.engine.lookup_userfunction(signature)
        return self.user_call(function, query, continuation)

    def CLEAR_LOCAL(self, stack, number):
        self.localvarcache[number] = None

    def UNIFY(self, stack):
        stack.pop().unify(stack.pop(), self.engine.heap)

    def user_call(self, function, query, continuation):
        assert isinstance(query, Callable)
        rulechain = function.rulechain
        if rulechain is None:
            error.throw_existence_error(
                "procedure", query.get_prolog_signature())
        oldstate = self.engine.heap.branch()
        while rulechain is not None:
            rule = rulechain.rule
            if rule.code.can_contain_cut:
                continuation = LimitedScopeContinuation(continuation)
                try:
                    frame = rule.make_frame(query)
                    return frame.run_directly(continuation)
                except error.UnificationFailed:
                    self.engine.heap.revert(oldstate)
                except error.CutException, e:
                    if continuation.scope_active:
                        return self.engine.continue_after_cut(e.continuation,
                                                              continuation)
                    raise
            else:
                try:
                    frame = rule.make_frame(query)
                    return frame.run_directly(continuation)
                except error.UnificationFailed:
                    self.engine.heap.revert(oldstate)
            rulechain = rulechain.next
        raise error.UnificationFailed

