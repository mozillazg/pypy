import py
from pypy.rlib.debug import ll_assert
from pypy.jit.rainbow.test import test_hotpath
from pypy.lang.prolog.interpreter import portal
from pypy.lang.prolog.interpreter import engine, term
from pypy.lang.prolog.interpreter.parsing import parse_query_term, get_engine

py.test.skip("fix me")
POLICY = portal.PyrologHintAnnotatorPolicy()

class TestPortal(test_hotpath.HotPathTest):
    small = False

    def test_simple(self):
        X = term.Var()
        Y = term.Var()
        larger = term.Term(
            "h", [term.Number(100), X])

        e = get_engine("""
            f(X) :- h(X, _).
            h(0, foo).
            h(X, Y) :- Z is X - 1, h(Z, Y).
        """)
        signature2function = e.signature2function
        parser = e.parser
        operations = e.operations
        def main(n):
            # XXX workaround for problems with prebuilt virtualizables
            e = engine.Engine()
            e.signature2function = signature2function
            e.parser = parser
            e.operations = operations
            if n == 0:
                e.call(term.Term("h", [term.Number(2), Y]))
                return isinstance(Y.dereference(e), term.Atom)
            if n == 1:
                e.call(larger)
                return isinstance(Y.dereference(e), term.Atom)
            else:
                return False

        res = main(0)
        assert res == True
        res = main(1)
        assert res == True


        res = self.run(main, [1], threshold=2, policy=POLICY)
        assert res == True
        
        res = self.run(main, [0], threshold=2, policy=POLICY)
        assert res == True

    def test_and(self):
        e = get_engine("""
            h(X) :- f(X).
            h(a).
            b(a).
            a(a).
            f(X) :- b(X), a(X).
            f(X) :- fail.
        """)
        X = term.Var()

        def main(n):
            e.reset()
            if n == 0:
                e.call(term.Term("h", [X]))
                return isinstance(X.dereference(e), term.Atom)
            else:
                return False

        res = main(0)
        assert res == True

        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [0], policy=POLICY,
                                         backendoptimize=True, 
                                         inline=0.0)
        assert res == True

    def test_append(self):
        e = get_engine("""
            append([], L, L).
            append([X|Y], L, [X|Z]) :- append(Y, L, Z).
        """)
        t = parse_query_term("append([a, b, c], [d, f, g], X).")
        X = term.Var()

        def main(n):
            if n == 0:
                e.call(t)
                return isinstance(X.dereference(e), term.Term)
            else:
                return False

        res = main(0)
        assert res == True

        e.reset()
        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [0], policy=POLICY,
                                         backendoptimize=True, 
                                         inline=0.0)
        assert res == True


    def test_user_call(self):
        e = get_engine("""
            h(X) :- f(X, b).
            f(a, a).
            f(X, b) :- g(X).
            g(b).
        """)
        X = term.Var()

        def main(n):
            e.reset()
            if n == 0:
                e.call(term.Term("h", [X]))
                return isinstance(X.dereference(e), term.Atom)
            else:
                return False

        res = main(0)
        assert res == True


        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [0], policy=POLICY,
                                         backendoptimize=True, 
                                         inline=0.0)
        assert res == True

    def test_loop(self):
        num = term.Number(50)

        def main(n):
            e.reset()
            if n == 0:
                e.call(term.Term("f", [num]))
                return True
            else:
                return False

        res = main(0)
        assert res
        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [0], policy=POLICY,
                                         backendoptimize=True, 
                                         inline=0.0)
        assert res

