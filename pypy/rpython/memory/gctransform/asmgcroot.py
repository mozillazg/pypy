from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.rpython.memory.gctransform.framework import BaseRootWalker
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
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
        return AsmStackRootWalker(self)


class AsmStackRootWalker(BaseRootWalker):

    def __init__(self, gctransformer):
        BaseRootWalker.__init__(self, gctransformer)

        def _asm_callback(initialframedata):
            self.walk_stack_from(initialframedata)
        self._asm_callback = _asm_callback

    def setup_root_walker(self):
        # The gcmap table is a list of pairs of pointers:
        #     void *SafePointAddress;
        #     void *Shape;
        # Here, i.e. when the program starts, we sort it
        # in-place on the SafePointAddress to allow for more
        # efficient searches.
        gcmapstart = llop.llvm_gcmapstart(llmemory.Address)
        gcmapend   = llop.llvm_gcmapend(llmemory.Address)
        insertion_sort(gcmapstart, gcmapend)

    def walk_stack_roots(self, collect_stack_root):
        gcdata = self.gcdata
        gcdata._gc_collect_stack_root = collect_stack_root
        pypy_asm_stackwalk(llhelper(ASM_CALLBACK_PTR, self._asm_callback))

    def walk_stack_from(self, initialframedata):
        curframe = lltype.malloc(WALKFRAME, flavor='raw')
        otherframe = lltype.malloc(WALKFRAME, flavor='raw')
        self.fill_initial_frame(curframe, initialframedata)
        # Loop over all the frames in the stack
        while self.walk_to_parent_frame(curframe, otherframe):
            swap = curframe
            curframe = otherframe    # caller becomes callee
            otherframe = swap
        lltype.free(otherframe, flavor='raw')
        lltype.free(curframe, flavor='raw')

    def fill_initial_frame(self, curframe, initialframedata):
        # Read the information provided by initialframedata
        reg = 0
        while reg < CALLEE_SAVED_REGS:
            # NB. 'initialframedata' stores the actual values of the
            # registers %ebx etc., and if these values are modified
            # they are reloaded by pypy_asm_stackwalk().  By contrast,
            # 'regs_stored_at' merely points to the actual values
            # from the 'initialframedata'.
            curframe.regs_stored_at[reg] = initialframedata + reg*sizeofaddr
            reg += 1
        curframe.frame_address = initialframedata.address[CALLEE_SAVED_REGS]

    def walk_to_parent_frame(self, callee, caller):
        """Starting from 'callee', walk the next older frame on the stack
        and fill 'caller' accordingly.  Also invokes the collect_stack_root()
        callback from the GC code for each GC root found in 'caller'.
        """
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

        retaddr = callee.frame_address.address[0]
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
        #
        # found!  Now we can go to the caller_frame.
        #
        shape = item.address[1]
        framesize = shape.signed[0]
        caller.frame_address = callee.frame_address + framesize
        #
        # enumerate the GC roots in the caller frame
        #
        collect_stack_root = self.gcdata._gc_collect_stack_root
        gc = self.gc
        LIVELOCS = 1 + CALLEE_SAVED_REGS + 1  # index of the first gc root loc
        livecount = shape.signed[LIVELOCS-1]
        while livecount > 0:
            livecount -= 1
            location = shape.signed[LIVELOCS + livecount]
            addr = self.getlocation(callee, caller, location)
            if addr.address[0] != llmemory.NULL:
                collect_stack_root(gc, addr)
        #
        # track where the caller_frame saved the registers from its own
        # caller
        #
        if shape.signed[1] == -1:     # a marker that means "I'm the frame
            return False              # of the entry point, stop walking"
        reg = 0
        while reg < CALLEE_SAVED_REGS:
            location = shape.signed[1+reg]
            addr = self.getlocation(callee, caller, location)
            caller.regs_stored_at[reg] = addr
            reg += 1
        return True

    def getlocation(self, callee, caller, location):
        """Get the location in the 'caller' frame of a variable, based
        on the integer 'location' that describes it.  The 'callee' is
        only used if the location is in a register that was saved in the
        callee.
        """
        if location & 1:     # register
            reg = location >> 1
            ll_assert(0 <= reg < CALLEE_SAVED_REGS, "bad register location")
            return callee.regs_stored_at[reg]
        else:
            # in the stack frame
            return caller.frame_address + location


# ____________________________________________________________

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

# ____________________________________________________________

#
# The special pypy_asm_stackwalk(), implemented directly in
# assembler, fills information about the current stack top in an
# ASM_FRAMEDATA array and invokes an RPython callback with it.
# An ASM_FRAMEDATA is an array of 5 values that describe everything
# we need to know about a stack frame:
#
#   - the value that %ebx had when the current function started
#   - the value that %esi had when the current function started
#   - the value that %edi had when the current function started
#   - the value that %ebp had when the current function started
#   - frame address (actually the addr of the retaddr of the current function;
#                    that's the last word of the frame in memory)
#
CALLEE_SAVED_REGS = 4       # there are 4 callee-saved registers
FRAME_PTR         = CALLEE_SAVED_REGS    # the frame is at index 4 in the array

ASM_CALLBACK_PTR = lltype.Ptr(lltype.FuncType([llmemory.Address],
                                              lltype.Void))

# used internally by walk_stack_from()
WALKFRAME = lltype.Struct('WALKFRAME',
        ('regs_stored_at',    # address of where the registers have been saved
             lltype.FixedSizeArray(llmemory.Address, CALLEE_SAVED_REGS)),
        ('frame_address',
             llmemory.Address),
    )

pypy_asm_stackwalk = rffi.llexternal('pypy_asm_stackwalk',
                                     [ASM_CALLBACK_PTR],
                                     lltype.Void,
                                     sandboxsafe=True,
                                     _nowrapper=True)
