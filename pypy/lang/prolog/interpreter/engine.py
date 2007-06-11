import py
from pypy.lang.prolog.interpreter.term import Var, Term, Atom, debug_print, \
    Callable
from pypy.lang.prolog.interpreter.error import UnificationFailed, \
    FunctionNotFound, CutException
from pypy.lang.prolog.interpreter import error, helper
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.jit import purefunction, hint

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

class TrailChunk(object):
    def __init__(self, last=None):
        self.last = last
        self.trail = []

    def __str__(self):
        return "TrailChunk(%s, %s)" % (self.last, self.trail)

class Trail(object):
    _virtualizable_ = True
    def __init__(self):
        self.current_chunk = TrailChunk()

    def reset(self):
        self.current_chunk = TrailChunk()

    def add_trail(self, var):
        self.current_chunk.trail.append((var, var.binding))

    def branch(self):
        result = TrailChunk(self.current_chunk)
        self.current_chunk = result
        return result

    def revert(self, chunk):
        curr = self.current_chunk
        while curr is not None:
            i = len(curr.trail) - 1
            while i >= 0:
                var, val = curr.trail[i]
                var.binding = val
                i -= 1
            if curr is chunk:
                break
            curr = curr.last
        else:
            self.current_chunk = TrailChunk()
            return
        self.current_chunk = chunk
        chunk.trail = []

    def newvar(self):
        result = Var()
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

    def __repr__(self):
        return "LinkedRules(%r, %r)" % (self.rule, self.next)


class Function(object):
    def __init__(self, signature, prolog_signature, firstrule=None):
        self.signature = signature
        self.prolog_signature = prolog_signature
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
        self.trail = Trail()
        self.signature2function = {}
        self.parser = None
        self.operations = None
        #XXX circular imports hack
        if not we_are_translated():
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
            self.signature2function[signature] = Function(
                signature, rule.head.get_prolog_signature(), rule)

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
        return frame.run_directly(continuation, choice_point)

    def lookup_userfunction(self, signature, prolog_signature=None):
        signature2function = self.signature2function
        function = signature2function.get(signature, None)
        if function is None:
            assert prolog_signature is not None
            signature2function[signature] = function = Function(
                signature, prolog_signature)
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

