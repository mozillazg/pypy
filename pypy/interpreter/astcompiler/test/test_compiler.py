import py
from pypy.interpreter.astcompiler import misc, pycodegen
from pypy.interpreter.pyparser.test.test_astbuilder import source2ast
from pypy.interpreter.pyparser.test import expressions
from pypy.interpreter.pycode import PyCode

def compile_with_astcompiler(expr, mode, space):
    ast = source2ast(expr, mode, space)
    misc.set_filename('<testing>', ast)
    if mode == 'exec':
        Generator = pycodegen.ModuleCodeGenerator
    elif mode == 'single':
        Generator = pycodegen.InteractiveCodeGenerator
    elif mode == 'eval':
        Generator = pycodegen.ExpressionCodeGenerator
    codegen = Generator(space, ast)
    rcode = codegen.getCode()
    assert isinstance(rcode, PyCode)
    assert rcode.co_filename == '<testing>'
    return rcode


class TestCompiler:
    """These tests compile snippets of code and check them by
    running them with our own interpreter.  These are thus not
    completely *unit* tests, but given that our interpreter is
    pretty stable now it is the best way I could find to check
    the compiler.
    """

    def run(self, source):
        source = str(py.code.Source(source))
        space = self.space
        code = compile_with_astcompiler(source, 'exec', space)
        w_dict = space.newdict()
        code.exec_code(space, w_dict, w_dict)
        return w_dict

    def check(self, w_dict, evalexpr, expected):
        # for now, we compile evalexpr with CPython's compiler but run
        # it with our own interpreter to extract the data from w_dict
        co_expr = compile(evalexpr, '<evalexpr>', 'eval')
        space = self.space
        pyco_expr = PyCode._from_code(space, co_expr)
        w_res = pyco_expr.exec_code(space, w_dict, w_dict)
        res = space.str_w(space.repr(w_res))
        assert res == repr(expected)

    def simple_test(self, source, evalexpr, expected):
        w_g = self.run(source)
        self.check(w_g, evalexpr, expected)

    st = simple_test

    def test_argtuple(self):
        yield (self.simple_test, "def f( x, (y,z) ): return x,y,z",
               "f((1,2),(3,4))", ((1,2),3,4))
        yield (self.simple_test, "def f( x, (y,(z,t)) ): return x,y,z,t",
               "f(1,(2,(3,4)))", (1,2,3,4))
        yield (self.simple_test, "def f(((((x,),y),z),t),u): return x,y,z,t,u",
               "f(((((1,),2),3),4),5)", (1,2,3,4,5))

    def test_constants(self):
        for c in expressions.constants:
            yield (self.simple_test, "x="+c, "x", eval(c))

    def test_tuple_assign(self):
        yield self.simple_test, "x,= 1,", "x", 1
        yield self.simple_test, "x,y = 1,2", "x,y", (1, 2)
        yield self.simple_test, "x,y,z = 1,2,3", "x,y,z", (1, 2, 3)
        yield self.simple_test, "x,y,z,t = 1,2,3,4", "x,y,z,t", (1, 2, 3, 4)
        yield self.simple_test, "x,y,x,t = 1,2,3,4", "x,y,t", (3, 2, 4)
        yield self.simple_test, "[x]= 1,", "x", 1
        yield self.simple_test, "[x,y] = [1,2]", "x,y", (1, 2)
        yield self.simple_test, "[x,y,z] = 1,2,3", "x,y,z", (1, 2, 3)
        yield self.simple_test, "[x,y,z,t] = [1,2,3,4]", "x,y,z,t", (1, 2, 3,4)
        yield self.simple_test, "[x,y,x,t] = 1,2,3,4", "x,y,t", (3, 2, 4)

    def test_binary_operator(self):
        for operator in ['+', '-', '*', '**', '/', '&', '|', '^', '//',
                         '<<', '>>', 'and', 'or']:
            expected = eval("17 %s 5" % operator)
            yield self.simple_test, "x = 17 %s 5" % operator, "x", expected
            expected = eval("0 %s 11" % operator)
            yield self.simple_test, "x = 0 %s 11" % operator, "x", expected

    def test_augmented_assignment(self):
        for operator in ['+', '-', '*', '**', '/', '&', '|', '^', '//',
                         '<<', '>>']:
            expected = eval("17 %s 5" % operator)
            yield self.simple_test, "x = 17; x %s= 5" % operator, "x", expected

    def test_subscript(self):
        yield self.simple_test, "d={2:3}; x=d[2]", "x", 3
        yield self.simple_test, "d={(2,):3}; x=d[2,]", "x", 3
        yield self.simple_test, "d={}; d[1]=len(d); x=d[len(d)]", "x", 0
        yield self.simple_test, "d={}; d[1]=3; del d[1]", "len(d)", 0

    def test_attribute(self):
        yield self.simple_test, """
            class A:
                pass
            a1 = A()
            a2 = A()
            a1.bc = A()
            a1.bc.de = a2
            a2.see = 4
            a1.bc.de.see += 3
            x = a1.bc.de.see
        """, 'x', 7

    def test_slice(self):
        decl = py.code.Source("""
            class A(object):
                def __getitem__(self, x):
                    global got
                    got = x.start, x.stop, x.step
                def __setitem__(self, x, y):
                    global set
                    set = x.start, x.stop, x.step
                def __delitem__(self, x):
                    global deleted
                    deleted = x.start, x.stop, x.step
            a = A()
        """)
        decl = str(decl) + '\n'
        yield self.st, decl + "a[:]", "got", (None, None, None)
        yield self.st, decl + "a[2:]", "got", (2, None, None)
        yield self.st, decl + "a[:2]", "got", (None, 2, None)
        yield self.st, decl + "a[4:7]", "got", (4, 7, None)
        yield self.st, decl + "a[::]", "got", (None, None, None)
        yield self.st, decl + "a[2::]", "got", (2, None, None)
        yield self.st, decl + "a[:2:]", "got", (None, 2, None)
        yield self.st, decl + "a[4:7:]", "got", (4, 7, None)
        yield self.st, decl + "a[::3]", "got", (None, None, 3)
        yield self.st, decl + "a[2::3]", "got", (2, None, 3)
        yield self.st, decl + "a[:2:3]", "got", (None, 2, 3)
        yield self.st, decl + "a[4:7:3]", "got", (4, 7, 3)

    def test_funccalls(self):
        decl = py.code.Source("""
            def f(*args, **kwds):
                kwds = kwds.items()
                kwds.sort()
                return list(args) + kwds
        """)
        decl = str(decl) + '\n'
        yield self.st, decl + "x=f()", "x", []
        yield self.st, decl + "x=f(5)", "x", [5]
        yield self.st, decl + "x=f(5, 6, 7, 8)", "x", [5, 6, 7, 8]
        yield self.st, decl + "x=f(a=2, b=5)", "x", [('a',2), ('b',5)]
        yield self.st, decl + "x=f(5, b=2, *[6,7])", "x", [5, 6, 7, ('b', 2)]
        yield self.st, decl + "x=f(5, b=2, **{'a': 8})", "x", [5, ('a', 8),
                                                                  ('b', 2)]

    def test_listmakers(self):
        yield (self.st,
               "l = [(j, i) for j in range(10) for i in range(j)"
               + " if (i+j)%2 == 0 and i%3 == 0]",
               "l",
               [(2, 0), (4, 0), (5, 3), (6, 0),
                (7, 3), (8, 0), (8, 6), (9, 3)])
