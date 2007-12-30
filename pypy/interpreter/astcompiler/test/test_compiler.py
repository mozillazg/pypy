import py
from pypy.interpreter.astcompiler import misc, pycodegen
from pypy.interpreter.pyparser.test.test_astbuilder import source2ast
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

    def test_argtuple_1(self):
        w_g = self.run("""def f( x, (y,z) ):
                              return x,y,z
                       """)
        self.check(w_g, "f((1,2),(3,4))", ((1,2),3,4))

    def test_argtuple_2(self):
        w_g = self.run("""def f( x, (y,(z,t)) ):
                              return x,y,z,t
                       """)
        self.check(w_g, "f(1,(2,(3,4)))", (1,2,3,4))

    def test_argtuple_3(self):
        w_g = self.run("""def f( ((((x,),y),z),t), u ):
                              return x,y,z,t,u
                       """)
        self.check(w_g, "f(((((1,),2),3),4),5)", (1,2,3,4,5))
