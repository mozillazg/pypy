import py, os
import autopath
from pypy.rlib.rsdl import RSDL, RIMG
from pypy.rpython.lltypesystem import rffi


def test_load_image():
    for filename in ["demo.jpg", "demo.png"]:
        image = RIMG.Load(os.path.join(autopath.this_dir, filename))
        assert image
        assert rffi.getintfield(image, 'c_w') == 17
        assert rffi.getintfield(image, 'c_h') == 23
        RSDL.FreeSurface(image)
