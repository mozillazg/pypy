import py
from pypy.lang.prolog.interpreter import engine, helper, term, error
from pypy.lang.prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# finding all solutions to a goal

class FindallContinuation(engine.Continuation):
    def __init__(self, template):
        self.found = []
        self.template = template

    def _call(self, engine):
        clone = self.template.getvalue(engine)
        self.found.append(clone)
        raise error.UnificationFailed()

def impl_findall(engine, template, goal, bag):
    oldstate = engine.branch()
    collector = FindallContinuation(template)
    try:
        engine.call(goal, collector)
    except error.UnificationFailed:
        engine.revert(oldstate)
    result = term.Atom.newatom("[]")
    for i in range(len(collector.found) - 1, -1, -1):
        copy = collector.found[i]
        d = {}
        copy = copy.copy(engine, d)
        result = term.Term(".", [copy, result])
    bag.unify(result, engine)
impl_findall._look_inside_me_ = False
expose_builtin(impl_findall, "findall", unwrap_spec=['raw', 'callable', 'raw'])
