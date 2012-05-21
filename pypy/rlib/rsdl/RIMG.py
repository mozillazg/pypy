import sys
from pypy.rpython.lltypesystem import rffi
from platformer.cbuild import ExternalCompilationInfo
from pypy.rlib.rsdl import RSDL


if sys.platform == 'darwin':
    eci = ExternalCompilationInfo(
        includes = ['SDL_image.h'],
        frameworks = ['SDL_image'],
        include_dirs = ['/Library/Frameworks/SDL_image.framework/Headers']
    )
else:
    eci = ExternalCompilationInfo(
        includes=['SDL_image.h'],
        libraries=['SDL_image'],
    )

eci = eci.merge(RSDL.eci)

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

Load = external('IMG_Load', [rffi.CCHARP], RSDL.SurfacePtr)
