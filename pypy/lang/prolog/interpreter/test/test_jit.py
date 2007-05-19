import py
from pypy.jit.timeshifter.test.test_portal import PortalTest, P_NOVIRTUAL
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


        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [1], policy=POLICY,
                                         backendoptimize=True)
        assert res == True
        
        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [0], policy=POLICY,
                                         backendoptimize=True)
        assert res == True

    def test_and(self):
        e = get_engine("""
            b(a).
            a(a).
            f(X) :- b(X), a(X).
            f(X) :- fail.
        """)
        X = e.heap.newvar()

        def main(n):
            e.heap.reset()
            if n == 0:
                e.call(term.Term("f", [X]))
                return isinstance(X.dereference(e.heap), term.Atom)
            else:
                return False

        res = main(0)
        assert res == True

        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [0], policy=POLICY,
                                         backendoptimize=True)
        assert res == True

    def test_user_call(self):
        e = get_engine("""
            h(X) :- f(X, b).
            f(a, a).
            f(X, b) :- g(X).
            g(b).
        """)
        X = e.heap.newvar()

        def main(n):
            e.heap.reset()
            if n == 0:
                e.call(term.Term("h", [X]))
                return isinstance(X.dereference(e.heap), term.Atom)
            else:
                return False

        res = main(0)
        assert res == True


        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [0], policy=POLICY,
                                         backendoptimize=True)
        assert res == True

