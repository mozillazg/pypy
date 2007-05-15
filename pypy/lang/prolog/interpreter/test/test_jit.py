import py
from pypy.jit.timeshifter.test.test_portal import PortalTest
from pypy.lang.prolog.interpreter import portal
from pypy.lang.prolog.interpreter import engine, term
from pypy.lang.prolog.interpreter.parsing import parse_query_term, get_engine

POLICY = portal.PyrologHintAnnotatorPolicy()


class TestPortal(PortalTest):
    small = False

    def test_simple(self):
        e = get_engine("""
            f(x, y).
            f(a(X), b(b(Y))) :- f(X, Y).
        """)
        X = e.heap.newvar()
        Y = e.heap.newvar()
        larger = term.Term(
            "f", [term.Term("a", [X]), term.Term("b", [term.Term("b", [Y])])])

        def main(n):
            e.heap.reset()
            if n == 0:
                e.call(term.Term("f", [X, Y]))
                return isinstance(X.dereference(e.heap), term.Atom)
            if n == 1:
                e.call(larger)
                return isinstance(X.dereference(e.heap), term.Atom)
            else:
                return False

        res = main(0)
        assert res == True
        res = main(1)
        assert res == True


        res = self.timeshift_from_portal(main, engine.Engine.try_rule.im_func,
                                         [1], policy=POLICY)
        assert res == True
        
        res = self.timeshift_from_portal(main, engine.Engine.try_rule.im_func,
                                         [0], policy=POLICY)
        assert res == True

