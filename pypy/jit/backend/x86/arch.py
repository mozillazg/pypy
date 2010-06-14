# Constants that depend on whether we are on 32-bit or 64-bit

import sys
if sys.maxint == (2**31 - 1):
    WORD = 4
    FRAME_FIXED_SIZE = 5     # ebp + ebx + esi + edi + force_index = 5 words
    FORCE_INDEX_OFS = -4*WORD
    IS_X86_32 = True
    IS_X86_64 = False
else:
    WORD = 8
    FRAME_FIXED_SIZE = 7
    FORCE_INDEX_OFS = -6*WORD
    IS_X86_32 = False
    IS_X86_64 = True
