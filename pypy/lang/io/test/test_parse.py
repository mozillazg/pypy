from pypy.lang.io.parserhack import parse, implicit, Ast

def test_simple():
    input = "a b c"
    ast = parse(input)
    assert ast == Ast(Ast(Ast(implicit, "a"), "b"), "c")
    
def test_simple_args():
    input = "a + b c"
    ast = parse(input)
    assert ast == Ast(Ast(implicit, "a"), '+', [Ast(Ast(implicit, 'b'), 'c')])

