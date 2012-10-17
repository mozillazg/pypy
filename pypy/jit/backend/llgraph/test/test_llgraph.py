import py
from pypy.rpython.lltypesystem import lltype, llmemory

from pypy.jit.codewriter import heaptracker
from pypy.jit.backend.test.runner_test import LLtypeBackendTest

class TestLLTypeLLGraph(LLtypeBackendTest):
    # for individual tests see:
    # ====> ../../test/runner_test.py
    
    from pypy.jit.backend.llgraph.runner import LLGraphCPU as cpu_type

    def setup_method(self, _):
        self.cpu = self.cpu_type(None)

    def test_cond_call_gc_wb(self):
        py.test.skip("does not make much sense on the llgraph backend")

    test_cond_call_gc_wb_array = test_cond_call_gc_wb
    test_cond_call_gc_wb_array_card_marking_fast_path = test_cond_call_gc_wb

    def test_backends_dont_keep_loops_alive(self):
        py.test.skip("does not make much sense on the llgraph backend")

    def test_memoryerror(self):
        py.test.skip("does not make much sense on the llgraph backend")


def test_cast_adr_to_int_and_back():
    X = lltype.Struct('X', ('foo', lltype.Signed))
    x = lltype.malloc(X, immortal=True)
    x.foo = 42
    a = llmemory.cast_ptr_to_adr(x)
    i = heaptracker.adr2int(a)
    assert lltype.typeOf(i) is lltype.Signed
    a2 = heaptracker.int2adr(i)
    assert llmemory.cast_adr_to_ptr(a2, lltype.Ptr(X)) == x
    assert heaptracker.adr2int(llmemory.NULL) == 0
    assert heaptracker.int2adr(0) == llmemory.NULL
