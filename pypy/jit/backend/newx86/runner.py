from pypy.jit.backend.llsupport.llmodel import AbstractLLCPU
from pypy.jit.backend.newx86.assembler import Assembler386


class CPU(AbstractLLCPU):

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)
        if opts is not None:
            self.failargs_limit = opts.failargs_limit
        else:
            self.failargs_limit = 1000

    def compile_loop(self, inputargs, operations, looptoken):
        """Assemble the given loop, and update looptoken to point to
        the compiled loop in assembler."""
        assembler = Assembler386(self)
        assembler.compile_loop(inputargs, operations, looptoken)
