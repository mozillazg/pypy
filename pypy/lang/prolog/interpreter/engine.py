from pypy.lang.prolog.interpreter.term import Var, Term, Rule, Atom, debug_print, \
    Callable
from pypy.lang.prolog.interpreter.error import UnificationFailed, FunctionNotFound, \
    CutException
from pypy.lang.prolog.interpreter import error
from pypy.rlib.jit import hint, we_are_jitted, _is_early_constant, \
    purefunction, JitDriver
from pypy.rlib.objectmodel import specialize
from pypy.rlib.unroll import unrolling_iterable

DEBUG = False

# bytecodes:
CALL = 'a'
USER_CALL = 'u'
TRY_RULE = 't'
CONTINUATION = 'c'
DONE = 'd'


class Continuation(object):
    def call(self, engine, choice_point=True):
        if choice_point:
            return engine.main_loop(CONTINUATION, None, self, None)
        return (CONTINUATION, None, self, None)

    def _call(self, engine):
        return (DONE, None, None, None)

DONOTHING = Continuation()

class LimitedScopeContinuation(Continuation):
    def __init__(self, continuation):
        self.scope_active = True
        self.continuation = continuation

    def _call(self, engine):
        self.scope_active = False
        return self.continuation.call(engine, choice_point=False)

class TrailChunk(object):
    _immutable_ = True
    def __init__(self, prev=None):
        self.trail = []
        self.prev = prev


class Heap(object):
    _mixin_ = True
    
    def reset(self):
        self.current_chunk = TrailChunk()
    __init__ = reset

    def add_trail(self, var):
        self.current_chunk.trail.append((var, var.binding))

    def branch(self):
        result = self.current_chunk
        self.current_chunk = TrailChunk(self.current_chunk)
        return result

    def revert(self, state):
        curr = self.current_chunk
        while curr is not state:
            for i in range(len(curr.trail) - 1, -1, -1):
                var, val = curr.trail[i]
                var.binding = val
            curr = curr.prev
        self.current_chunk = TrailChunk(curr)

    def discard(self, state):
        pass #XXX for now

class LinkedRules(object):
    _immutable_ = True
    def __init__(self, rule, next=None):
        self.rule = rule
        self.next = next

    def copy(self, stopat=None):
        first = LinkedRules(self.rule)
        curr = self.next
        copy = first
        while curr is not stopat:
            new = LinkedRules(curr.rule)
            copy.next = new
            copy = new
            curr = curr.next
        return first, copy

    def find_applicable_rule(self, uh2):
        #import pdb;pdb.set_trace()
        while self:
            uh = self.rule.unify_hash
            hint(uh, concrete=True)
            uh = hint(uh, deepfreeze=True)
            j = 0
            while j < len(uh):
                hint(j, concrete=True)
                hash1 = uh[j]
                hash2 = uh2[j]
                if hash1 != 0 and hash2 * (hash2 - hash1) != 0:
                    break
                j += 1
            else:
                return self
            self = self.next
        return None

    def __repr__(self):
        return "LinkedRules(%r, %r)" % (self.rule, self.next)



class Function(object):
    def __init__(self, firstrule=None):
        if firstrule is None:
            self.rulechain = self.last = None
        else:
            self.rulechain = LinkedRules(firstrule)
            self.last = self.rulechain

    def add_rule(self, rule, end):
        if self.rulechain is None:
            self.rulechain = self.last = LinkedRules(rule)
        elif end:
            self.rulechain, last = self.rulechain.copy()
            self.last = LinkedRules(rule)
            last.next = self.last
        else:
            self.rulechain = LinkedRules(rule, self.rulechain)

    def remove(self, rulechain):
        self.rulechain, last = self.rulechain.copy(rulechain)
        last.next = rulechain.next


class Engine(Heap):
    _virtualizable_ = True

    def __init__(self):
        self.reset()
        self.signature2function = {}
        self.parser = None
        self.operations = None

    def add_rule(self, rule, end=True):
        from pypy.lang.prolog import builtin
        if DEBUG:
            debug_print("add_rule", rule)
        if isinstance(rule, Term):
            if rule.name == ":-":
                rule = Rule(rule.args[0], rule.args[1])
            else:
                rule = Rule(rule, None)
            signature = rule.signature
        elif isinstance(rule, Atom):
            rule = Rule(rule, None)
            signature = rule.signature
        else:
            error.throw_type_error("callable", rule)
            assert 0, "unreachable" # make annotator happy
        if signature in builtin.builtins:
            error.throw_permission_error(
                "modify", "static_procedure", rule.head.get_prolog_signature())
        function = self.signature2function.get(signature, None)
        if function is not None:
            self.signature2function[signature].add_rule(rule, end)
        else:
            self.signature2function[signature] = Function(rule)

    def run(self, query, continuation=DONOTHING):
        if not isinstance(query, Callable):
            error.throw_type_error("callable", query)
        try:
            return self.call(query, continuation, choice_point=True)
        except CutException, e:
            return self.continue_after_cut(e.continuation)

    def _build_and_run(self, tree):
        from pypy.lang.prolog.interpreter.parsing import TermBuilder
        builder = TermBuilder()
        term = builder.build_query(tree)
        if isinstance(term, Term) and term.name == ":-" and len(term.args) == 1:
            self.run(term.args[0])
        else:
            self.add_rule(term)
        return self.parser

    def runstring(self, s):
        from pypy.lang.prolog.interpreter.parsing import parse_file
        trees = parse_file(s, self.parser, Engine._build_and_run, self)

    def call(self, query, continuation=DONOTHING, choice_point=True):
        assert isinstance(query, Callable)
        if not choice_point:
            return (CALL, query, continuation, None)
        return self.main_loop(CALL, query, continuation)

    def _call(self, query, continuation):
        signature = query.signature
        signature = hint(signature, promote=True)
        builtin = _jit_builtin_lookup(signature)
        if builtin is not None:
            return builtin.call(self, query, continuation)
        return self.user_call(query, continuation, choice_point=False)

    def jit_main_loop(self, where, query, continuation, rule=None):
        next = (DONE, None, None, None)
        while 1:
            myjitdriver.jit_merge_point(where=where, continuation=continuation,
                                        query=query, rule=rule, _self=self,
                                        next=next)
            hint(where, concrete=True)
            hint(rule, concrete=True)
            if where == DONE:
                return next
            next = self.dispatch_bytecode(next, where, query, continuation, rule)
            where, query, continuation, rule = next
            where = hint(where, promote=True)
            rule = hint(rule, promote=True)

    def main_loop(self, where, query, continuation, rule=None):
        return self.jit_main_loop(where, query, continuation, rule)
    main_loop._look_inside_me_ = False

    def dispatch_bytecode(self, next, where, query, continuation, rule):
        if where == CALL:
            next = self._call(query, continuation)
        elif where == TRY_RULE:
            # XXX seems a slightly strange place to put it
            myjitdriver.can_enter_jit(where=where, continuation=continuation,
                                      query=query, rule=rule, _self=self,
                                      next=next)
            next = self._try_rule(rule, query, continuation)
        elif where == USER_CALL:
            next = self._user_call(query, continuation)
        elif where == CONTINUATION:
            hint(continuation.__class__, promote=True)
            next = continuation._call(self)
        else:
            raise Exception("unknown bytecode")
        return next

    def _lookup(self, signature):
        signature2function = self.signature2function
        signature2function = hint(signature2function, promote=True)
        return _jit_lookup(signature2function, signature)

    def user_call(self, query, continuation, choice_point=True):
        if not choice_point:
            return (USER_CALL, query, continuation, None)
        return self.main_loop(USER_CALL, query, continuation)

    def _user_call(self, query, continuation):
        signature = hint(query.signature, promote=True)
        function = self._lookup(signature)
        startrulechain = function.rulechain
        startrulechain = hint(startrulechain, promote=True)
        if startrulechain is None:
            error.throw_existence_error(
                "procedure", query.get_prolog_signature())

        unify_hash = query.unify_hash_of_children(self)
        rulechain = startrulechain.find_applicable_rule(unify_hash)
        if rulechain is None:
            # none of the rules apply
            raise UnificationFailed()
        rule = rulechain.rule
        rulechain = rulechain.next
        oldstate = self.branch()
        while 1:
            if rulechain is not None:
                rulechain = rulechain.find_applicable_rule(unify_hash)
                choice_point = rulechain is not None
            else:
                choice_point = False
            hint(rule, concrete=True)
            if rule.contains_cut:
                continuation = LimitedScopeContinuation(continuation)
                try:
                    result = self.try_rule(rule, query, continuation)
                    self.discard(oldstate)
                    return result
                except UnificationFailed:
                    self.revert(oldstate)
                except CutException, e:
                    if continuation.scope_active:
                        return self.continue_after_cut(e.continuation,
                                                       continuation)
                    raise
            else:
                try:
                    # for the last rule (rulechain is None), this will always
                    # return, because choice_point is False
                    result = self.try_rule(rule, query, continuation,
                                           choice_point=choice_point)
                    self.discard(oldstate)
                    return result
                except UnificationFailed:
                    assert choice_point
                    self.revert(oldstate)
            rule = rulechain.rule
            rulechain = rulechain.next

    def try_rule(self, rule, query, continuation=DONOTHING, choice_point=True):
        if not choice_point:
            return (TRY_RULE, query, continuation, rule)
        return self.main_loop(TRY_RULE, query, continuation, rule)

    def _try_rule(self, rule, query, continuation):
        rule = hint(rule, deepfreeze=True)
        # standardizing apart
        nextcall = rule.clone_and_unify_head(self, query)
        if nextcall is not None:
            return self.call(nextcall, continuation, choice_point=False)
        else:
            return continuation.call(self, choice_point=False)

    def continue_after_cut(self, continuation, lsc=None):
        while 1:
            try:
                return continuation.call(self, choice_point=True)
            except CutException, e:
                if lsc is not None and not lsc.scope_active:
                    raise
                continuation = e.continuation

    def parse(self, s):
        from pypy.lang.prolog.interpreter.parsing import parse_file, TermBuilder, lexer
        builder = TermBuilder()
        trees = parse_file(s, self.parser)
        terms = builder.build_many(trees)
        return terms, builder.varname_to_var

    def getoperations(self):
        from pypy.lang.prolog.interpreter.parsing import default_operations
        if self.operations is None:
            return default_operations
        return self.operations


@purefunction
def _jit_builtin_lookup(signature):
    from pypy.lang.prolog.builtin import builtins
    return builtins.get(signature, None)


@purefunction
def _jit_lookup(signature2function, signature):
    function = signature2function.get(signature, None)
    if function is None:
        signature2function[signature] = function = Function()
    return function

class MyJitDriver(JitDriver):
    reds = ['continuation', 'query', 'next', '_self']
    greens = ['where', 'rule']
    
    def on_enter_jit(self, invariant, reds, where, rule):
        reds._self.branch()

myjitdriver = MyJitDriver()
