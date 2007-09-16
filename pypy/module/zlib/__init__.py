
"""
Mixed-module definition for the zlib module.
"""

import zlib

from pypy.interpreter.mixedmodule import MixedModule

def constant(value):
    return 'space.wrap(%s)' % (value,)


class Module(MixedModule):
    interpleveldefs = {
        'crc32': 'interp_zlib.crc32',
        'adler32': 'interp_zlib.adler32',
        'Compress': 'interp_zlib.Compress',
        'Decompress': 'interp_zlib.Decompress',
        }

#     # Constants exposed by zlib.h
#     interpleveldefs.update((
#             (name, constant(getattr(zlib, name)))
#             for name
#             in ['DEFLATED', 'DEF_MEM_LEVEL', 'MAX_WBITS',
#                 'Z_BEST_COMPRESSION', 'Z_BEST_SPEED',
#                 'Z_DEFAULT_COMPRESSION', 'Z_DEFAULT_STRATEGY',
#                 'Z_FILTERED', 'Z_FINISH', 'Z_FULL_FLUSH',
#                 'Z_HUFFMAN_ONLY', 'Z_NO_FLUSH', 'Z_SYNC_FLUSH']))

    appleveldefs = {
        'error': 'app_zlib.error',
        'compress': 'app_zlib.compress',
        'decompress': 'app_zlib.decompress',
        'compressobj': 'app_zlib.compressobj',
        'decompressobj': 'app_zlib.decompressobj',
        }
