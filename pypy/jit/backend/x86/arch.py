# Constants that depend on whether we are on 32-bit or 64-bit

# The frame size gives the standard fixed part at the start of
# every assembler frame: the saved value of some registers,
# one word for the force_index, and some extra space used only
# during a malloc that needs to go via its slow path.

import sys
if sys.maxint == (2**31 - 1):
    WORD = 4
    # ebp + ebx + esi + edi + 4 extra words + force_index = 9 words
    FRAME_FIXED_SIZE = 9
    FORCE_INDEX_OFS = -8*WORD
    MY_COPY_OF_REGS = -7*WORD
    IS_X86_32 = True
    IS_X86_64 = False
else:
    WORD = 8
    # rbp + rbx + r12 + r13 + r14 + r15 + 11 extra words + force_index = 18
    FRAME_FIXED_SIZE = 18
    FORCE_INDEX_OFS = -17*WORD
    MY_COPY_OF_REGS = -16*WORD
    IS_X86_32 = False
    IS_X86_64 = True

# The extra space has room for almost all registers, apart from eax and edx
# which are used in the malloc itself.  They are:
#   ecx, ebx, esi, edi               [32 and 64 bits]
#   r8, r9, r10, r12, r13, r14, r15    [64 bits only]
#
# Note that with asmgcc, the locations corresponding to callee-save registers
# are never used.

# In the offstack version (i.e. when using stacklets): the off-stack allocated
# area starts with the FRAME_FIXED_SIZE words in the same order as they would
# be on the real stack (which is top-to-bottom, so it's actually the opposite
# order as the one in the comments above); but whereas the real stack would
# have the spilled values stored in (ebp-20), (ebp-24), etc., the off-stack
# has them stored in (ebp+8), (ebp+12), etc.
OFFSTACK_START_AT_WORD = 2
#
# In stacklet mode, the real frame contains always just OFFSTACK_REAL_FRAME
# words reserved for temporary usage like call arguments.  To maintain
# alignment on 32-bit, OFFSTACK_REAL_FRAME % 4 == 3, and it is at least 17
# to handle all other cases.
OFFSTACK_REAL_FRAME = 19
