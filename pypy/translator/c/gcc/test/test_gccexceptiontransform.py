from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.simplify import join_blocks
from pypy.translator.c.gcc import gccexceptiontransform
from pypy.translator.c.genc import CStandaloneBuilder
from pypy import conftest
from pypy.annotation.listdef import s_list_of_strings

def get_translator(fn, backendopt=False):
    t = TranslationContext()
    t.buildannotator().build_types(fn, [s_list_of_strings])
    t.buildrtyper().specialize()
    if backendopt:
        backend_optimizations(t)
    return t

def transform_func(fn, backendopt=False):
    t = get_translator(fn, backendopt)
    g = graphof(t, fn)
    if conftest.option.view:
        g.show()
    etrafo = gccexceptiontransform.ExceptionTransformer(t)
    etrafo.create_exception_handling(g)
    join_blocks(g)
    if conftest.option.view:
        t.view()
    # 't' is not used; instead we usually build a new translator in compile().

def compile(fn, backendopt=False):
    t = get_translator(fn, backendopt)
    t.config.translation.exceptions = "asmgcc"
    cbuilder = CStandaloneBuilder(t, fn, t.config)
    cbuilder.generate_source()
    cbuilder.compile()
    res = t.platform.execute(cbuilder.executable_name, '')
    out = res.out
    if res.returncode != 0:
        out += '***' + res.err
    return out


def test_passthrough():
    def one(x):
        if x:
            raise ValueError()
    def foo(argv):
        one(0)
        print "before raising"
        one(1)
        print "after raising"
        one(0)
        return 0

    transform_func(foo)
    data = compile(foo)
    assert data == "before raising\n***Fatal RPython error: ValueError\n"
