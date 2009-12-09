from pypy.translator.sepcomp import scimport
from pypy.module.md5demo.interp_md5 import RMD5Interface

MD5Interface = scimport(RMD5Interface)
del RMD5Interface
