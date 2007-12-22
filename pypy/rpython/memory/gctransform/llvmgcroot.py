from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython import rmodel
from pypy.rpython.rbuiltin import gen_cast
from pypy.rlib.debug import ll_assert


#
#  This implements a StackRootWalker based on the data produced by
#  the llvm GC plug-in found over there:
#
#     http://codespeak.net/svn/user/arigo/hack/pypy-hack/stackrootwalker
#


class LLVMGcRootFrameworkGCTransformer(FrameworkGCTransformer):
    # XXX this is completely specific to the llvm backend at the moment.

    def push_roots(self, hop, keep_current_args=False):
        livevars = self.get_livevars_for_roots(hop, keep_current_args)
        self.num_pushs += len(livevars)
        if not livevars:
            return []
        for k, var in enumerate(livevars):
            c_k = rmodel.inputconst(lltype.Signed, k)
            v_adr = gen_cast(hop.llops, llmemory.Address, var)
            hop.genop("llvm_store_gcroot", [c_k, v_adr])
        return livevars

    def pop_roots(self, hop, livevars):
        if not livevars:
            return
        if self.gcdata.gc.moving_gc:
            # for moving collectors, reload the roots into the local variables
            for k, var in enumerate(livevars):
                c_k = rmodel.inputconst(lltype.Signed, k)
                v_newaddr = hop.genop("llvm_load_gcroot", [c_k],
                                      resulttype=llmemory.Address)
                hop.genop("gc_reload_possibly_moved", [v_newaddr, var])
        # XXX for now, the values stay in the gcroots.  It might keep
        # some old objects alive for a bit longer than necessary.

    def build_stack_root_iterator(self):
        sizeofaddr = llmemory.sizeof(llmemory.Address)
        gcdata = self.gcdata

        class StackRootIterator:
            _alloc_flavor_ = 'raw'

            def setup_root_stack():
                pass
            setup_root_stack = staticmethod(setup_root_stack)

            need_root_stack = False

            def append_static_root(adr):
                gcdata.static_root_end.address[0] = adr
                gcdata.static_root_end += sizeofaddr
            append_static_root = staticmethod(append_static_root)
            
            def __init__(self, with_static=True):
                self.stack_current = llop.llvm_frameaddress(llmemory.Address)
                self.remaining_roots_in_current_frame = 0
                if with_static:
                    self.static_current = gcdata.static_root_end
                else:
                    self.static_current = gcdata.static_root_nongcend

            def pop(self):
                while self.static_current != gcdata.static_root_start:
                    self.static_current -= sizeofaddr
                    result = self.static_current.address[0]
                    if result.address[0] != llmemory.NULL:
                        return result

                while True:
                    while self.remaining_roots_in_current_frame == 0:
                        if not self.walk_to_parent_frame():
                            return llmemory.NULL
                    result = self.next_gcroot_from_current_frame()
                    if result.address[0] != llmemory.NULL:
                        return result

            def walk_to_parent_frame(self):
                #
                # The gcmap table is a list of pairs of pointers:
                #     void *SafePointAddress;
                #     void *Shape;
                #
                # A "safe point" is the return address of a call.
                # The "shape" of a safe point records the size of the
                # frame of the function containing it, as well as a
                # list of the variables that contain gc roots at that
                # time.  Each variable is described by its offset in
                # the frame.
                #
                callee_frame = self.stack_current
                #
                # XXX the details are completely specific to X86!!!
                # a picture of the stack may help:
                #                                           ^ ^ ^
                #     |     ...      |                 to older frames
                #     +--------------+
                #     |  first word  |  <------ caller_frame (addr of 1st word)
                #     +              +
                #     | caller frame |
                #     |     ...      |
                #     |  frame data  |  <------ frame_data_base
                #     +--------------+
                #     |   ret addr   |
                #     +--------------+
                #     |  first word  |  <------ callee_frame (addr of 1st word)
                #     +              +
                #     | callee frame |
                #     |     ...      |
                #     |  frame data  |                 lower addresses
                #     +--------------+                      v v v
                #
                retaddr = callee_frame.address[1]
                #
                # try to locate the caller function based on retaddr.
                # XXX this is just a linear scan for now, that's
                # incredibly bad.
                #
                gcmapstart = llop.llvm_gcmapstart(llmemory.Address)
                gcmapend   = llop.llvm_gcmapend(llmemory.Address)
                while gcmapstart != gcmapend:
                    if gcmapstart.address[0] == retaddr:
                        #
                        # found!  Setup pointers allowing us to
                        # parse the caller's frame structure...
                        #
                        shape = gcmapstart.address[1]
                        # XXX assumes that .signed is 32-bit
                        framesize = shape.signed[0]
                        livecount = shape.signed[1]
                        caller_frame = callee_frame + 4 + framesize
                        self.stack_current = caller_frame
                        self.frame_data_base = callee_frame + 8
                        self.remaining_roots_in_current_frame = livecount
                        self.liveoffsets = shape + 8
                        return True

                    gcmapstart += 2 * sizeofaddr

                # retaddr not found.  Assume that this is the system function
                # that called the original entry point, i.e. it's the end of
                # the stack for us
                return False

            def next_gcroot_from_current_frame(self):
                i = self.remaining_roots_in_current_frame - 1
                self.remaining_roots_in_current_frame = i
                ll_assert(i >= 0, "bad call to next_gcroot_from_current_frame")
                liveoffset = self.liveoffsets.signed[i]
                return self.frame_data_base + liveoffset


        return StackRootIterator
