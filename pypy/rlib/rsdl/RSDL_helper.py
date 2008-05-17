from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rsdl import RSDL

def get_rgb(color, format):
    rgb = lltype.malloc(rffi.CArray(RSDL.Uint8), 3, flavor='raw')
    try:
        RSDL.GetRGB(color,
                    format,
                    rffi.ptradd(rgb, 0),
                    rffi.ptradd(rgb, 1),
                    rffi.ptradd(rgb, 2))
        r = rffi.cast(lltype.Signed, rgb[0])
        g = rffi.cast(lltype.Signed, rgb[1])
        b = rffi.cast(lltype.Signed, rgb[2])
        result = r, g, b
    finally:
        lltype.free(rgb, flavor='raw')

    return result

def get_rgba(color, format):
    rgb = lltype.malloc(rffi.CArray(RSDL.Uint8), 4, flavor='raw')
    try:
        RSDL.GetRGBA(color,
                    format,
                    rffi.ptradd(rgb, 0),
                    rffi.ptradd(rgb, 1),
                    rffi.ptradd(rgb, 2),
                    rffi.ptradd(rgb, 3))
        r = rffi.cast(lltype.Signed, rgb[0])
        g = rffi.cast(lltype.Signed, rgb[1])
        b = rffi.cast(lltype.Signed, rgb[2])
        a = rffi.cast(lltype.Signed, rgb[3])
        result = r, g, b, a
    finally:
        lltype.free(rgb, flavor='raw')

    return result
