from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.tool import rffi_platform as platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo

eci = ExternalCompilationInfo(
    includes = ['SDL.h'],
    include_dirs = ['/usr/include/SDL'],
    libraries = ['SDL'],
)

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

class CConfig:
    _compilation_info_ = eci

    Uint32 = platform.SimpleType('Uint32', rffi.INT)

    INIT_VIDEO = platform.ConstantInteger('SDL_INIT_VIDEO')

globals().update(platform.configure(CConfig))


Init = external('SDL_Init', [Uint32], rffi.INT)
Quit = external('SDL_Quit', [], lltype.Void)
