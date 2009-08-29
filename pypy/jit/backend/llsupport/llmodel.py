from pypy.jit.backend.model import AbstractCPU
from pypy.jit.backend.llsupport.descr import get_field_descr, get_array_descr


class AbstractLLCPU(AbstractCPU):

    def __init__(self, rtyper, stats, translate_support_code=False,
                 gcdescr=None):
        from pypy.jit.backend.llsupport.gc import get_ll_description
        self.rtyper = rtyper
        self.stats = stats
        self.translate_support_code = translate_support_code
        self.gc_ll_descr = get_ll_description(gcdescr, self)

    def fielddescrof(self, STRUCT, fieldname):
        return get_field_descr(STRUCT, fieldname, self.translate_support_code)

    def arraydescrof(self, A):
        return get_array_descr(A)
