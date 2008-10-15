
from pypy.translator.platform.distutils_platform import DistutilsPlatform

class Windows(DistutilsPlatform):
    name = "win32"
    so_ext = 'dll'

