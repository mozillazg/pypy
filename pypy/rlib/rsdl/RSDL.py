from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.tool import rffi_platform as platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo
import sys

if sys.platform == 'darwin':
    eci = ExternalCompilationInfo(
        includes = ['SDL.h'],
        include_dirs = ['/Library/Frameworks/SDL.framework/Versions/A/Headers'],
        link_extra = [
            'macosx-sdl-main/SDLMain.m',
            '-I', '/Library/Frameworks/SDL.framework/Versions/A/Headers',
        ],
        frameworks = ['SDL', 'Cocoa']
    )
else:
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
    Uint16 = platform.SimpleType('Uint16', rffi.INT)
    Uint32 = platform.SimpleType('Uint32', rffi.INT)

    BYTEORDER = platform.ConstantInteger('SDL_BYTEORDER')
    BIG_ENDIAN = platform.ConstantInteger('SDL_BIG_ENDIAN')
    INIT_VIDEO = platform.ConstantInteger('SDL_INIT_VIDEO')

    Rect = platform.Struct('SDL_Rect', [('x', rffi.INT),
                                        ('y', rffi.INT),
                                        ('w', rffi.INT),
                                        ('h', rffi.INT)])
    Surface = platform.Struct('SDL_Surface', [('w', rffi.INT),
                                              ('h', rffi.INT),
                                              ('format', PixelFormatPtr),
                                              ('pitch', rffi.INT),
                                              ('pixels', rffi.UCHARP)])
    PixelFormat = platform.Struct('SDL_PixelFormat',
                                  [('BytesPerPixel', rffi.INT)])

globals().update(platform.configure(CConfig))

RectPtr.TO.become(Rect)
SurfacePtr.TO.become(Surface)
PixelFormatPtr.TO.become(PixelFormat)

Uint8P = lltype.Ptr(lltype.Array(Uint8, hints={'nolength': True}))
Uint16P = lltype.Ptr(lltype.Array(Uint16, hints={'nolength': True}))
Uint32P = lltype.Ptr(lltype.Array(Uint32, hints={'nolength': True}))

def Init(flags):
    if sys.platform == 'darwin':
        from AppKit import NSApplication
        NSApplication.sharedApplication()
    return _Init(flags)

_Init = external('SDL_Init', [Uint32], rffi.INT)
Quit = external('SDL_Quit', [], lltype.Void)
SetVideoMode = external('SDL_SetVideoMode', [rffi.INT, rffi.INT,
                                             rffi.INT, Uint32],
                        SurfacePtr)
WM_SetCaption = external('SDL_WM_SetCaption', [rffi.CCHARP, rffi.CCHARP],
                         lltype.Void)
Flip = external('SDL_Flip', [SurfacePtr], rffi.INT)
CreateRGBSurface = external('SDL_CreateRGBSurface', [Uint32, rffi.INT,
                                                     rffi.INT, rffi.INT,
                                                     Uint32, Uint32,
                                                     Uint32, Uint32],
                            SurfacePtr)
LockSurface = external('SDL_LockSurface', [SurfacePtr], rffi.INT)
UnlockSurface = external('SDL_UnlockSurface', [SurfacePtr], lltype.Void)
FreeSurface = external('SDL_FreeSurface', [SurfacePtr], lltype.Void)

MapRGB = external('SDL_MapRGB', [PixelFormatPtr, Uint8, Uint8, Uint8], Uint32)
GetRGB = external('SDL_GetRGB', [Uint32, PixelFormatPtr,
                                 Uint8P, Uint8P, Uint8P], lltype.Void)
FillRect = external('SDL_FillRect', [SurfacePtr, RectPtr, Uint32], rffi.INT)
BlitSurface = external('SDL_UpperBlit', [SurfacePtr, RectPtr, SurfacePtr, RectPtr], rffi.INT)

def getpixel(image, x, y):
    """Return the pixel value at (x, y)
    NOTE: The surface must be locked before calling this!
    """
    bpp = rffi.getintfield(image.c_format, 'c_BytesPerPixel')
    pitch = rffi.getintfield(image, 'c_pitch')
    # Here p is the address to the pixel we want to retrieve
    p = rffi.ptradd(image.c_pixels, y * pitch + x * bpp)
    if bpp == 1:
        return rffi.cast(Uint32, p[0])
    elif bpp == 2:
        p = rffi.cast(Uint16P, p)
        return rffi.cast(Uint32, p[0])
    elif bpp == 3:
        p0 = rffi.cast(lltype.Signed, p[0])
        p1 = rffi.cast(lltype.Signed, p[1])
        p2 = rffi.cast(lltype.Signed, p[2])
        if BYTEORDER == BIG_ENDIAN:
            result = p0 << 16 | p1 << 8 | p2
        else:
            result = p0 | p1 << 8 | p2 << 16
        return rffi.cast(Uint32, result)
    elif bpp == 4:
        p = rffi.cast(Uint32P, p)
        return p[0]
    else:
        raise ValueError("bad BytesPerPixel")
