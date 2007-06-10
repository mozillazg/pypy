import py
from pypy.jit.hintannotator.policy import ManualGraphPolicy
from pypy.lang.prolog.interpreter import term, engine, helper, interpreter, \
    prologopcode
from pypy.translator.translator import graphof
from pypy.annotation.specialize import getuniquenondirectgraph


forbidden_modules = {'pypy.lang.prolog.interpreter.parser': True,
                     }

good_modules = {'pypy.lang.prolog.builtin.control': True,
                'pypy.lang.prolog.builtin.register': True
               }


PORTAL = interpreter.Frame.run_jit.im_func

class PyrologHintAnnotatorPolicy(ManualGraphPolicy):
    PORTAL = PORTAL
    def look_inside_graph_of_module(self, graph, func, mod):
        if "unify__" in graph.name:
            return True
        if mod in forbidden_modules:
            return False
        if mod in good_modules:
            return True
        if mod.startswith("pypy.lang.prolog"):
            return False
        return True

    def fill_timeshift_graphs(self, portal_graph):
        import pypy
        for cls in [term.Var, term.Term, term.Number, term.Atom, term.LocalVar]:
            self.seegraph(cls.__init__)
        for cls in [term.Var, term.LocalVar]:
            self.seegraph(cls.setvalue)
        for cls in [term.Term, term.Number, term.Atom, term.Var]:
            self.seegraph(cls.dereference)
        for cls in [term.Var, term.Term, term.Number, term.Atom]:
            self.seegraph(cls.eval_arithmetic)
        for cls in [term.Callable, term.Atom, term.Term]:
            self.seegraph(cls.get_prolog_signature)
        self.seegraph(PORTAL)
        self.seegraph(engine.Heap.newvar)
        self.seegraph(engine.TrailChunk.__init__)
        self.seegraph(interpreter.Rule.make_frame)
        for method in "branch revert newvar add_trail".split():
            self.seegraph(getattr(engine.Heap, method))
        for method in ("unify_head run_directly run user_call "
                       "dispatch_bytecode getcode jit_enter_function "
                       "__init__ _run").split():
            self.seegraph(getattr(interpreter.Frame, method))
        for num in prologopcode.allopcodes:
            method = prologopcode.opname[num]
            if method == "DYNAMIC_CALL":
                continue
            self.seegraph(getattr(interpreter.Frame, method))
        self.seegraph(engine.Continuation.call)
        for cls in [engine.Continuation, engine.LimitedScopeContinuation,
                    pypy.lang.prolog.builtin.control.AndContinuation,
                    interpreter.FrameContinuation
                    ]:
            self.seegraph(cls._call)
        self.seegraph(interpreter.FrameContinuation.__init__)
        for function in "".split():
            self.seegraph(getattr(helper, function))

def get_portal(drv):
    t = drv.translator
    portal = getattr(PORTAL, 'im_func', PORTAL)

    policy = PyrologHintAnnotatorPolicy()
    policy.seetranslator(t)
    return portal, policy
