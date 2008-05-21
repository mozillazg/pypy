import py, os
import autopath
from pypy.rlib.rsdl import RSDL, RMix, RSDL_helper
from pypy.rpython.lltypesystem import lltype, rffi

def test_open_mixer():
    if RMix.OpenAudio(22050, RSDL.AUDIO_S16LSB, 2, 1024) != 0:
        error = rffi.charp2str(RSDL.GetError())
        raise Exception(error)
