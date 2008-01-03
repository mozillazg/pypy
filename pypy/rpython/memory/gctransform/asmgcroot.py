from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython import rmodel
from pypy.rpython.rbuiltin import gen_cast
from pypy.rlib.debug import ll_assert


#
#  This transformer avoids the use of a shadow stack in a completely
#  platform-specific way, by directing genc to insert asm() special
#  instructions in the C source, which are recognized by GCC.
#  The .s file produced by GCC is then parsed by trackgcroot.py.
#


class AsmGcRootFrameworkGCTransformer(FrameworkGCTransformer):

    def push_roots(self, hop, keep_current_args=False):
        livevars = self.get_livevars_for_roots(hop, keep_current_args)
        self.num_pushs += len(livevars)
        return livevars

    def pop_roots(self, hop, livevars):
        if not livevars:
            return
        # mark the values as gc roots
        for var in livevars:
            hop.genop("asm_gcroot", [var])

    def build_root_walker(self):
        gcdata = self.gcdata
        gc = gcdata.gc

        class RootWalker:
            _alloc_flavor_ = 'raw'

            def setup_root_stack(self):
                # The gcmap table is a list of pairs of pointers:
                #     void *SafePointAddress;
                #     void *Shape;
                # Here, i.e. when the program starts, we sort it
                # in-place on the SafePointAddress to allow for more
                # efficient searches.
                gcmapstart = llop.llvm_gcmapstart(llmemory.Address)
                gcmapend   = llop.llvm_gcmapend(llmemory.Address)
                insertion_sort(gcmapstart, gcmapend)

            need_root_stack = False

            def append_static_root(adr):
                gcdata.static_root_end.address[0] = adr
                gcdata.static_root_end += sizeofaddr
            append_static_root = staticmethod(append_static_root)

            def walk_roots(self, collect_stack_root,
                           collect_static_in_prebuilt_nongc,
                           collect_static_in_prebuilt_gc,
                           collect_finished):
                ...
                self.callee_data = lltype.malloc(ASM_STACKWALK, flavor="raw")
                self.caller_data = lltype.malloc(ASM_STACKWALK, flavor="raw")
                pypy_asm_stackwalk_init(self.caller_data)
                self.remaining_roots_in_current_frame = 0
                # We must walk at least a couple of frames up the stack
                # *now*, i.e. before we leave __init__, otherwise
                # the caller_data ends up pointing to a dead frame.
                # We can walk until we find a real GC root; then we're
                # definitely out of the GC code itself.
                while self.remaining_roots_in_current_frame == 0:
                    if not self.walk_to_parent_frame():
                        break     # not a single GC root? unlikely but not
                                  # impossible I guess
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
                if not self.caller_data:
                    return False
                #
                # The gcmap table is a list of pairs of pointers:
                #     void *SafePointAddress;
                #     void *Shape;
                #
                # A "safe point" is the return address of a call.
                # The "shape" of a safe point is a list of integers
                # as follows:
                #
                #   * The size of the frame of the function containing the
                #     call (in theory it can be different from call to call).
                #     This size includes the return address (see picture
                #     below).
                #
                #   * Four integers that specify where the function saves
                #     each of the four callee-saved registers (%ebx, %esi,
                #     %edi, %ebp).  This is a "location", see below.
                #
                #   * The number of live GC roots around the call.
                #
                #   * For each GC root, an integer that specify where the
                #     GC pointer is stored.  This is a "location", see below.
                #
                # A "location" can be either in the stack or in a register.
                # If it is in the stack, it is specified as an integer offset
                # from the current frame (so it is typically < 0, as seen
                # in the picture below, though it can also be > 0 if the
                # location is an input argument to the current function and
                # thus lives at the bottom of the caller's frame).
                # A "location" can also be in a register; in our context it
                # can only be a callee-saved register.  This is specified
                # as a small odd-valued integer (1=%ebx, 3=%esi, etc.)

                # In the code below, we walk the next older frame on the stack.
                # The caller becomes the callee; we swap the two buffers and
                # fill in the new caller's data.
                callee = self.caller_data
                caller = self.callee_data
                self.caller_data = caller
                self.callee_data = callee
                #
                # XXX the details are completely specific to X86!!!
                # a picture of the stack may help:
                #                                           ^ ^ ^
                #     |     ...      |                 to older frames
                #     +--------------+
                #     |   ret addr   |  <------ caller_frame (addr of retaddr)
                #     |     ...      |
                #     | caller frame |
                #     |     ...      |
                #     +--------------+
                #     |   ret addr   |  <------ callee_frame (addr of retaddr)
                #     |     ...      |
                #     | callee frame |
                #     |     ...      |                 lower addresses
                #     +--------------+                      v v v
                #
                callee_frame = callee[FRAME_PTR]
                retaddr = callee[RET_ADDR]
                #
                # try to locate the caller function based on retaddr.
                #
                gcmapstart = llop.llvm_gcmapstart(llmemory.Address)
                gcmapend   = llop.llvm_gcmapend(llmemory.Address)
                item = binary_search(gcmapstart, gcmapend, retaddr)
                if item.address[0] != retaddr:
                    # retaddr not found!
                    llop.debug_fatalerror(lltype.Void, "cannot find gc roots!")
                    return False

                # found!  Now we can fill in 'caller'.
                shape = item.address[1]
                framesize = shape.signed[0]
                caller[FRAME_PTR] = callee_frame + framesize
                caller[RET_ADDR] = caller[FRAME_PTR].address[0]
                reg = 0
                while reg < CALLEE_SAVED_REGS:
                    caller[reg] = self.read_from_location(shape.signed[1+reg])
                    reg += 1
                livecount = shape.signed[1+CALLEE_SAVED_REGS]
                self.remaining_roots_in_current_frame = livecount
                self.liveoffsets = shape + 4 * (1+CALLEE_SAVED_REGS+1)
                return True

            def finished(self):
                lltype.free(self.stackwalkcur, flavor='raw')
                self.stackwalkcur = lltype.nullptr(ASM_STACKWALK)
                lltype.free(self.stackwalknext, flavor='raw')
                self.stackwalknext = lltype.nullptr(ASM_STACKWALK)

            def next_gcroot_from_current_frame(self):
                i = self.remaining_roots_in_current_frame - 1
                self.remaining_roots_in_current_frame = i
                ll_assert(i >= 0, "bad call to next_gcroot_from_current_frame")
                liveoffset = self.liveoffsets.signed[i]
                return self.callee_data[FRAME_PTR] + liveoffset

        return RootWalker()


sizeofaddr = llmemory.sizeof(llmemory.Address)
arrayitemsize = 2 * sizeofaddr


def binary_search(start, end, addr1):
    """Search for an element in a sorted array.

    The interval from the start address (included) to the end address
    (excluded) is assumed to be a sorted arrays of pairs (addr1, addr2).
    This searches for the item with a given addr1 and returns its
    address.
    """
    count = (end - start) // arrayitemsize
    while count > 1:
        middleindex = count // 2
        middle = start + middleindex * arrayitemsize
        if addr1 < middle.address[0]:
            count = middleindex
        else:
            start = middle
            count -= middleindex
    return start

def insertion_sort(start, end):
    """Sort an array of pairs of addresses.

    This is an insertion sort, so it's slowish unless the array is mostly
    sorted already (which is what I expect, but XXX check this).
    """
    next = start
    while next < end:
        # assuming the interval from start (included) to next (excluded)
        # to be already sorted, move the next element back into the array
        # until it reaches its proper place.
        addr1 = next.address[0]
        addr2 = next.address[1]
        scan = next
        while scan > start and addr1 < scan.address[-2]:
            scan.address[0] = scan.address[-2]
            scan.address[1] = scan.address[-1]
            scan -= arrayitemsize
        scan.address[0] = addr1
        scan.address[1] = addr2
        next += arrayitemsize

#
# The special pypy_asm_stackwalk_init(), implemented directly in
# assembler, initializes an ASM_STACKWALK array in order to bootstrap
# the stack walking code.  An ASM_STACKWALK is an array of 6 values
# that describe everything we need to know about a stack frame:
#
#   - the value that %ebx had when the current function started
#   - the value that %esi had when the current function started
#   - the value that %edi had when the current function started
#   - the value that %ebp had when the current function started
#   - frame address (actually the addr of the retaddr of the current function;
#                    that's the last word of the frame in memory)
#   - the return address for when the current function finishes
#                   (which is usually just the word at "frame address")
#
CALLEE_SAVED_REGS = 4       # there are 4 callee-saved registers
FRAME_PTR      = CALLEE_SAVED_REGS
RET_ADDR       = CALLEE_SAVED_REGS + 1
ASM_STACKWALK  = lltype.FixedSizeArray(llmemory.Address, CALLEE_SAVED_REGS + 2)

pypy_asm_stackwalk_init = rffi.llexternal('pypy_asm_stackwalk_init',
                                          [lltype.Ptr(ASM_STACKWALK)],
                                          lltype.Void,
                                          sandboxsafe=True,
                                          _nowrapper=True)
