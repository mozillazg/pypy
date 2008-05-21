from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.tool import rffi_platform as platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.rsdl import RSDL

eci = ExternalCompilationInfo(
    includes=['SDL_mixer.h'],
    libraries=['SDL_mixer'],
    )
eci = eci.merge(RSDL.eci)

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

OpenAudio = external('Mix_OpenAudio',
                [rffi.INT, RSDL.Uint16, rffi.INT, rffi.INT],
                rffi.INT)
