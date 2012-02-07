from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.translator.backendopt.support import var_needsgc


class StmFrameworkGCTransformer(FrameworkGCTransformer):

    def setup_write_barriers(self, GCClass, s_gc):
        self.write_barrier_ptr = None
        self.write_barrier_from_array_ptr = None
        pass  # xxx

    def gct_getfield(self, hop):
        if self.var_needs_set_transform(hop.spaceop.args[0]):
            hop.rename('stm_' + hop.spaceop.opname)
        else:
            self.default(hop)
    gct_getarrayitem = gct_getfield
    gct_getinteriorfield = gct_getfield


    def gct_gc_writebarrier_before_copy(self, hop):
        xxx
