from pypy.lang.prolog.interpreter import helper
from pypy.lang.prolog.interpreter import error
from pypy.lang.prolog.interpreter.term import Term, Atom, Var, Callable, \
    LocalVar
from pypy.lang.prolog.interpreter.engine import Continuation, \
    LimitedScopeContinuation, DONOTHING
from pypy.lang.prolog.interpreter.prologopcode import unrolling_opcode_descs, \
    HAVE_ARGUMENT
from pypy.rlib.jit import hint, we_are_jitted, _is_early_constant, purefunction

class FrameContinuation(Continuation):
    def __init__(self, frame, pc, continuation):
        self.frame = frame
        self.pc = pc
        self.continuation = continuation

    def _call(self, engine):
        return self.frame.run(self.frame.code, False, self.pc,
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

    def make_frame(self, stack):
        f = Frame(self.engine, self.code)
        f.unify_head(stack)
        return f

    def __repr__(self):
        if self.body is None:
            return "%s." % (self.head, )
        return "%s :- %s." % (self.head, self.body)


def dynamic_call_frame(engine, query):
    from pypy.lang.prolog.interpreter.compiler import Code
    frame = Frame(engine, Code.dynamic_code)
    frame.localvarcache[0] = query
    return frame


class Frame(object):
    _virtualizable_ = True

    def __init__(self, engine, code):
        self.engine = engine
        self.heap = engine.heap
        self.code = code
        self.localvarcache = [None] * code.maxlocalvar
        self.result = None

    def getcode(self):
        return hint(hint(self.code, promote=True), deepfreeze=True)

    def unify_head(self, stack):
        self.run(self.getcode(), True, 0, None)
        result = self.result
        if len(result):
            i = 0
            # These should be early constants, really
            m = hint(len(result), promote=True)
            startfrom = hint(len(stack) - m, promote=True)
            while i < m:
                hint(i, concrete=True)
                result[i].unify(stack[startfrom + i], self.heap)
                i += 1
        self.result = None

    def run_directly(self, continuation, choice_point=True):
        if not choice_point:
            if self.getcode().opcode:
                continuation = FrameContinuation(self, 0, continuation)
            return continuation
        if self.getcode().opcode:
            continuation = self.run(self.getcode(), False, 0, continuation)
        while continuation is not DONOTHING:
            continuation = continuation._call(self.engine)
        return DONOTHING

    def run(self, codeobject, head, pc, continuation):
        from pypy.lang.prolog.interpreter.compiler import Code
        if codeobject is Code.dynamic_code:
            return self._run(codeobject, head, pc, continuation)
        if head:
            return self._run(codeobject, head, pc, continuation)
        if not we_are_jitted():
            assert codeobject is not None
            return self.run_jit(self.heap, codeobject, head, pc, continuation)
        return self.opaque_run(codeobject, head, pc, continuation)

    def opaque_run(self, codeobject, head, pc, continuation):
        return self.run_jit(self.heap, codeobject, head, pc, continuation)
    opaque_run._look_inside_me = False

    def jit_enter_function(self):
        # funnyness
        code = self.getcode()
        localvarcache = [None] * code.maxlocalvar
        i = code.maxlocalvar
        while True:
            i -= 1
            if i < 0:
                break
            hint(i, concrete=True)
            obj = self.localvarcache[i]
            localvarcache[i] = obj
        self.localvarcache = localvarcache

    def run_jit(self, heap, codeobject, head, pc, continuation):
        hint(None, global_merge_point=True)
        hint(codeobject, concrete=True)
        codeobject = hint(codeobject, deepfreeze=True)
        hint(head, concrete=True)
        if head:
            bytecode = codeobject.opcode_head
            pc = 0
        else:
            bytecode = codeobject.opcode
            pc = hint(pc, promote=True)
        self.code = codeobject
        self.heap = heap

        self.jit_enter_function()
        stack = []
        while pc < len(bytecode):
            hint(None, global_merge_point=True)
            opcode = ord(bytecode[pc])
            pc += 1
            if opcode >= HAVE_ARGUMENT:
                hi = ord(bytecode[pc])
                lo = ord(bytecode[pc+1])
                pc += 2
                oparg = (hi << 8) | lo
            else:
                oparg = 0
            hint(opcode, concrete=True)
            hint(oparg, concrete=True)
            #import pdb; pdb.set_trace()
            res = self.dispatch_bytecode(opcode, oparg, bytecode, pc,
                                         stack, continuation)
            if res is not None:
                continuation = res
                while continuation is not DONOTHING:
                    if isinstance(continuation, FrameContinuation):
                        self = continuation.frame
                        bytecode = self.getcode().opcode
                        pc = hint(continuation.pc, promote=True)
                        continuation = continuation.continuation
                        stack = []
                        break
                    else:
                        continuation = continuation._call(self.engine)
        if head:
            self.result = stack
        return continuation

    def _run(self, codeobject, head, pc, continuation):
        codeobject = hint(codeobject, promote=True)
        codeobject = hint(codeobject, deepfreeze=True)
        hint(head, concrete=True)
        if head:
            bytecode = codeobject.opcode_head
            pc = 0
        else:
            bytecode = codeobject.opcode
            pc = hint(pc, promote=True)
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
            hint(opcode, concrete=True)
            hint(oparg, concrete=True)
            #import pdb; pdb.set_trace()
            res = self.dispatch_bytecode(opcode, oparg, bytecode, pc,
                                         stack, continuation)
            if res is not None:
                continuation = res
                while continuation is not DONOTHING:
                    if isinstance(continuation, FrameContinuation):
                        self = continuation.frame
                        bytecode = self.getcode().opcode
                        pc = hint(continuation.pc, promote=True)
                        continuation = continuation.continuation
                        stack = []
                        break
                    else:
                        continuation = continuation._call(self.engine)
        if head:
            self.result = stack
        return continuation


    def dispatch_bytecode(self, opcode, oparg, bytecode, pc, stack,
                          continuation):
        hint(opcode, concrete=True)
        hint(oparg, concrete=True)
        for opdesc in unrolling_opcode_descs:
            if opcode == opdesc.index:
                # dispatch to the opcode method
                meth = getattr(self, opdesc.name)
                if opdesc.hascontinuation:
                    if pc >= len(bytecode):
                        cont = continuation
                    else:
                        cont = FrameContinuation(self, pc, continuation)
                    if opdesc.hasargument:
                        return meth(stack, oparg, cont)
                    else:
                        return meth(stack, cont)
                else:
                    if opdesc.hasargument:
                        return meth(stack, oparg)
                    else:
                        return meth(stack)
                break
        else:
            raise error.UncatchableError("bytecode corruption")

    def PUTCONSTANT(self, stack, number):
        stack.append(self.getcode().constants[number])

    def MAKELOCALVAR(self, stack, number):
        result = self.localvarcache[number] = LocalVar()
        stack.append(result)

    def PUTLOCALVAR(self, stack, number):
        result = self.localvarcache[number]
        assert result is not None
        stack.append(result)

    def ACTIVATE_LOCAL(self, stack, number):
        var = self.localvarcache[number]
        assert var.__class__ == LocalVar
        self.localvarcache[number] = result = var.dereference(self.heap)
        hint(result.__class__, promote=True)
        var.active = True

    def MAKETERM(self, stack, number):
        name, numargs, signature = self.getcode().term_info[number]
        args = [None] * numargs
        i = numargs - 1
        while i >= 0:
            hint(i, concrete=True)
            args[i] = stack.pop()
            i -= 1
        stack.append(Term(name, args, signature))

    def CALL_BUILTIN(self, stack, number, continuation):
        from pypy.lang.prolog.builtin import builtins_list
        builtin = builtins_list[number][1]
        result = builtin.call(self.engine, stack, continuation)
        i = 0
        while i < builtin.numargs:
            hint(i, concrete=True)
            stack.pop()
            i += 1
        return result

    def CUT(self, stack, continuation):
        raise error.CutException(continuation)
    
    def STATIC_CALL(self, stack, number, continuation):
        function = self.getcode().functions[number]
        return self.user_call(function, stack, continuation)

    def DYNAMIC_CALL(self, stack, continuation):
        query = stack.pop()
        assert isinstance(query, Callable)
        signature = query.signature
        from pypy.lang.prolog.builtin import builtins
        if signature in builtins:
            builtin = builtins[signature]
            if isinstance(query, Term):
                args = query.args
            else:
                args = None
            return builtin.call(self.engine, args, continuation)
        function = self.engine.lookup_userfunction(
            signature, query.get_prolog_signature())
        if isinstance(query, Term):
            args = query.args
        else:
            args = None
        return self.user_call(function, args, continuation)

    def CLEAR_LOCAL(self, stack, number):
        self.localvarcache[number] = None

    def UNIFY(self, stack):
        stack.pop().unify(stack.pop(), self.heap)

    def user_call(self, function, args, continuation):
        rulechain = function.rulechain
        rulechain = hint(rulechain, promote=True)
        if rulechain is None:
            error.throw_existence_error(
                "procedure", function.prolog_signature)
        oldstate = self.heap.branch()
        while rulechain is not None:
            rule = rulechain.rule
            choice_point = rulechain.next is not None
            hint(rule, concrete=True)
            if rule.code.can_contain_cut:
                continuation = LimitedScopeContinuation(continuation)
                try:
                    frame = rule.make_frame(args)
                    result = frame.run_directly(continuation)
                    return result
                except error.UnificationFailed:
                    self.heap.revert(oldstate)
                except error.CutException, e:
                    if continuation.scope_active:
                        return self.engine.continue_after_cut(e.continuation,
                                                              continuation)
                    raise
            else:
                try:
                    frame = rule.make_frame(args)
                    result = frame.run_directly(continuation, choice_point)
                    return result
                except error.UnificationFailed:
                    self.heap.revert(oldstate)
                    if not choice_point:
                        raise
            rulechain = rulechain.next
