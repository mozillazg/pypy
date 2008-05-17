from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.tool import rffi_platform as platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo

eci = ExternalCompilationInfo(
    includes=['SDL.h'],
    )
eci = eci.merge(ExternalCompilationInfo.from_config_tool('sdl-config'))

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)

RectPtr        = lltype.Ptr(lltype.ForwardReference())
SurfacePtr     = lltype.Ptr(lltype.ForwardReference())
PixelFormatPtr = lltype.Ptr(lltype.ForwardReference())

class CConfig:
    _compilation_info_ = eci

    Uint8  = platform.SimpleType('Uint8',  rffi.INT)
    Uint32 = platform.SimpleType('Uint32', rffi.INT)

    INIT_VIDEO = platform.ConstantInteger('SDL_INIT_VIDEO')

    Rect = platform.Struct('SDL_Rect', [('x', rffi.INT),
                                        ('y', rffi.INT),
                                        ('w', rffi.INT),
                                        ('h', rffi.INT)])
    Surface = platform.Struct('SDL_Surface', [('w', rffi.INT),
                                              ('h', rffi.INT),
                                              ('format', PixelFormatPtr)])
    PixelFormat = platform.Struct('SDL_PixelFormat', [])

globals().update(platform.configure(CConfig))

RectPtr.TO.become(Rect)
SurfacePtr.TO.become(Surface)
PixelFormatPtr.TO.become(PixelFormat)


Init = external('SDL_Init', [Uint32], rffi.INT)
Quit = external('SDL_Quit', [], lltype.Void)
SetVideoMode = external('SDL_SetVideoMode', [rffi.INT, rffi.INT,
                                             rffi.INT, Uint32],
                        SurfacePtr)
Flip = external('SDL_Flip', [SurfacePtr], rffi.INT)
CreateRGBSurface = external('SDL_CreateRGBSurface', [Uint32, rffi.INT,
                                                     rffi.INT, rffi.INT,
                                                     Uint32, Uint32,
                                                     Uint32, Uint32],
                            SurfacePtr)
FreeSurface = external('SDL_FreeSurface', [SurfacePtr], lltype.Void)

MapRGB = external('SDL_MapRGB', [PixelFormatPtr, Uint8, Uint8, Uint8], Uint32)
FillRect = external('SDL_FillRect', [SurfacePtr, RectPtr, Uint32], rffi.INT)
