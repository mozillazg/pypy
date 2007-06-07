import py
from pypy.lang.prolog.interpreter.term import Var, Term, Atom, debug_print, \
    Callable
from pypy.lang.prolog.interpreter.error import UnificationFailed, \
    FunctionNotFound, CutException
from pypy.lang.prolog.interpreter import error, helper
from pypy.rlib.jit import hint, we_are_jitted, _is_early_constant, purefunction
from pypy.rlib.objectmodel import specialize
from pypy.rlib.unroll import unrolling_iterable

DEBUG = False

class Continuation(object):
    def call(self, engine, choice_point=True):
        if not choice_point:
            return self
        while self is not None:
            self = self._call(engine)

    def _call(self, engine):
        pass

DONOTHING = Continuation()

class LimitedScopeContinuation(Continuation):
    def __init__(self, continuation):
        self.scope_active = True
        self.continuation = continuation

    def _call(self, engine):
        self.scope_active = False
        return self.continuation

class Heap(object):
    def __init__(self):
        self.trail = []

    def reset(self):
        self.trail = []
        self.last_branch = 0

    def add_trail(self, var):
        self.trail.append((var, var.binding))

    def branch(self):
        return len(self.trail)

    def revert(self, state):
        trails = state
        for i in range(len(self.trail) - 1, trails - 1, -1):
            var, val = self.trail[i]
            var.binding = val
        del self.trail[trails:]

    def discard(self, state):
        pass #XXX for now

    def newvar(self):
        result = Var(self)
        return result

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


class Engine(object):
    def __init__(self):
        self.heap = Heap()
        self.signature2function = {}
        self.parser = None
        self.operations = None
        #XXX circular imports hack
        from pypy.lang.prolog.builtin import builtins_list
        globals()['unrolling_builtins'] = unrolling_iterable(builtins_list) 

    def add_rule(self, rule, end=True):
        from pypy.lang.prolog import builtin
        from pypy.lang.prolog.interpreter.interpreter import Rule
        if DEBUG:
            debug_print("add_rule", rule)
        if isinstance(rule, Term):
            if rule.name == ":-":
                rule = Rule(rule.args[0], rule.args[1], self)
            else:
                rule = Rule(rule, None, self)
        elif isinstance(rule, Atom):
            rule = Rule(rule, None, self)
        else:
            error.throw_type_error("callable", rule)
            assert 0, "unreachable" # make annotator happy
        signature = rule.signature
        if signature in builtin.builtins:
            error.throw_permission_error(
                "modify", "static_procedure", rule.head.get_prolog_signature())
        function = self.signature2function.get(signature, None)
        if function is not None:
            self.signature2function[signature].add_rule(rule, end)
        else:
            self.signature2function[signature] = Function(rule)

    def run(self, query, continuation=DONOTHING):
        from pypy.lang.prolog.interpreter.interpreter import dynamic_call_frame
        query = helper.ensure_callable(query)
        frame = dynamic_call_frame(self, query)
        try:
            frame.run_directly(continuation)
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
        from pypy.lang.prolog.interpreter.interpreter import dynamic_call_frame
        query = helper.ensure_callable(query)
        frame = dynamic_call_frame(self, query)
        #XXX handle choice_point correctly
        return frame.run_directly(continuation)

    @purefunction
    def lookup_userfunction(self, signature):
        signature2function = self.signature2function
        function = signature2function.get(signature, None)
        if function is None:
            signature2function[signature] = function = Function()
        return function

    def continue_after_cut(self, continuation, lsc=None):
        while 1:
            try:
                return continuation.call(self, choice_point=True)
            except CutException, e:
                if lsc is not None and not lsc.scope_active:
                    raise
                continuation = e.continuation

    def parse(self, s):
        from pypy.lang.prolog.interpreter.parsing import parse_file, TermBuilder
        builder = TermBuilder()
        trees = parse_file(s, self.parser)
        terms = builder.build_many(trees)
        return terms, builder.varname_to_var

    def getoperations(self):
        from pypy.lang.prolog.interpreter.parsing import default_operations
        if self.operations is None:
            return default_operations
        return self.operations

