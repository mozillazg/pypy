from pypy.lang.prolog.interpreter import helper
from pypy.lang.prolog.interpreter.term import Term, Atom, Var
from pypy.lang.prolog.interpreter.engine import CONTINUATION, Continuation
from pypy.lang.prolog.interpreter.prologopcode import unrolling_opcode_descs, \
    HAVE_ARGUMENT

class FrameContinuation(Continuation):
    def __init__(self, frame, pc):
        self.frame = frame
        self.pc = pc

    def _call(self, engine):
        return frame.run(pc)

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


class Frame(object):
    #_immutable_ = True # XXX?

    def __init__(self, engine, code):
        self.engine = engine
        self.code = code
        self.localvarcache = [None] * code.maxlocalvar

    def unify_head(self, head):
        self.run(self.code.opcode_head, 0, None, [head])

    def run(self, bytecode, pc, continuation, stack=None):
        if stack is None:
            stack = []
        while pc < len(bytecode):
            opcode = ord(bytecode[pc])
            pc += 1
            if opcode >= HAVE_ARGUMENT:
                lo = ord(bytecode[pc])
                hi = ord(bytecode[pc+1])
                pc += 2
                oparg = (hi << 8) | lo
            else:
                oparg = 0
            for opdesc in unrolling_opcode_descs:
                if opcode == opdesc.index:
                    # dispatch to the opcode method
                    meth = getattr(self, opdesc.name)
                    if opdesc.hascontinuation:
                        continuation = FrameContinuation(
                            self, pc, continuation)
                        if opdesc.hasargument:
                            res = meth(stack, oparg, continuation)
                        else:
                            res = meth(stack, continuation)
                    else:
                        if opdesc.hasargument:
                            res = meth(stack, oparg)
                        else:
                            res = meth(stack)
                    if res is not None:
                        while 1:
                            where, _, continuation, _ = res
                            assert where == CONTINUATION
                            if isinstance(continuation, FrameContinuation):
                                self = continuation.frame
                                pc = continuation.pc
                                bytecode = self.code.bytecode
                                stack = []
                            else:
                                res = continuation._call(self.engine)
                    break
            else:
                assert 0, "missing opcode"
        assert len(stack) == 0
        return (CONTINUATION, None, continuation, None)

    def PUTCONSTANT(self, stack, number):
        stack.append(self.code.constants[number])

    def PUTLOCALVAR(self, stack, number):
        result = self.localvarcache[number]
        if result is None:
            result = self.localvarcache[number] = self.engine.heap.newvar()
        stack.append(result)

    def MAKETERM(self, stack, number, *ignored):
        name, numargs, signature = self.code.term_info[number]
        args = [None] * numargs
        i = 0
        while i < numargs:
            args[i] = stack.pop()
            i += 1
        stack.append(Term(name, args, signature))

    def CALL_BUILTIN(self, stack, number, continuation, *ignored):
        from pypy.lang.prolog.builtin import builtins_list
        return builtins_list[number].call(self, stack.pop(), continuation)
    
    def DYNAMIC_CALL(self, stack, continuation, *ignored):
        query = stack.pop()
        function = self.engine._jit_lookup(signature)
        rulechain = function.rulechain
        if rulechain is None:
            error.throw_existence_error(
                "procedure", query.get_prolog_signature())
        oldstate = self.heap.branch()
        while rulechain is not None:
            rule = rulechain.rule
            try:
                frame = rule.make_frame(query)
                if frame.code.bytecode:
                    return frame.run(continuation)
                return None
            except UnificationFailed:
                self.heap.revert(oldstate)
            rule = rulechain.rule
            rulechain = rulechain.next

    def CLEAR_LOCAL(self, stack, number, *ignored):
        self.localvarcache[number] = None

    def UNIFY(self, stack, *ignored):
        stack.pop().unify(stack.pop(), self.engine.heap)


