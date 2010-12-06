from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.rpython.memory.gctransform.framework import BaseRootWalker
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython import annlowlevel

#
# This transformer works by letting the C backend handles most of the actual
# code, which cannot be easily expressed as regular low-level operations and
# types.
#
#   struct {
#     struct pypy_stackref_s hdr;
#     type1 var1;
#     ...
#     typeN varN;
#   } ref;
#


class InlineStackFrameworkGCTransformer(FrameworkGCTransformer):

    def push_roots(self, hop, keep_current_args=False):
        livevars = self.get_livevars_for_roots(hop, keep_current_args)
        hop.genop("gc_push_roots", livevars)
        return livevars

    def pop_roots(self, hop, livevars):
        pass

    def build_root_walker(self):
        return InlineStackRootWalker(self)

##    def gct_direct_call(self, hop):
##        fnptr = hop.spaceop.args[0].value
##        try:
##            close_stack = fnptr._obj._callable._gctransformer_hint_close_stack_
##        except AttributeError:
##            close_stack = False
##        if close_stack:
##            self.handle_call_with_close_stack(hop)
##        else:
##            FrameworkGCTransformer.gct_direct_call(self, hop)

##    def handle_call_with_close_stack(self, hop):
##        xxx


class InlineStackRootWalker(BaseRootWalker):

    def need_thread_support(self, gctransformer, getfn):
        pass

    def walk_stack_roots(self, collect_stack_root):
        gc = self.gc
        stackref = get_pypy_stackref()
        while stackref:
            bitfield = stackref.unsigned[1]
            index = 2
            while bitfield != 0:
                if bitfield & 1:
                    addr = stackref + index * llmemory.sizeof(llmemory.Address)
                    if gc.points_to_valid_gc_object(addr):
                        collect_stack_root(gc, addr)
                bitfield >>= 1
                index += 1
            stackref = stackref.address[0]

get_pypy_stackref = rffi.llexternal('get_pypy_stackref', [],
                                    llmemory.Address,
                                    sandboxsafe=True,
                                    _nowrapper=True)
