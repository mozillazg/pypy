from pypy.translator.stackless.transform import StacklessTransfomer
from pypy.rpython.memory.gctransform import varoftype
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.translator.translator import TranslationContext, graphof
from pypy.objspace.flow.model import checkgraph
from pypy import conftest

## def test_frame_types():
##     st = StacklessTransfomer(None)

##     signed = varoftype(lltype.Signed)
##     ptr = varoftype(lltype.Ptr(lltype.GcStruct("S")))
##     addr = varoftype(llmemory.Address)
##     float = varoftype(lltype.Float)
##     longlong = varoftype(lltype.SignedLongLong)

##     ft4vars = st.frame_type_for_vars
    
##     s1 = ft4vars([signed])
##     assert 'header' in s1._flds
##     assert len(s1._flds) == 2

##     s2_1 = ft4vars([signed, ptr])
##     s2_2 = ft4vars([ptr, signed])

##     assert s2_1 is s2_2

def test_simple_transform():
    from pypy.translator.stackless.code import UnwindException
    def check(x):
        if x:
            raise UnwindException # XXX or so
    def g(x):
        check(x)
        return 2
    def example(x):
        return g(x) + x + 1
    t = TranslationContext()
    t.buildannotator().build_types(example, [int])
    t.buildrtyper().specialize()
    st = StacklessTransfomer(t)
    st.transform_graph(graphof(t, example))
    st.transform_graph(graphof(t, g))
    for graph in t.graphs: 
        checkgraph(graph) # XXX
    example_graph = graphof(t, example)
    if conftest.option.view:
        t.view()
    
