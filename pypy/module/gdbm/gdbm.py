from pypy.rpython.tool import rffi_platform as platform
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.lltypesystem.rffi import llexternal, CCHARP, ExternalCompilationInfo, CStructPtr, INT
from pypy.rpython.lltypesystem.lltype import Signed, Ptr, Char, GcStruct, Void, OpaqueType, malloc
from pypy.rpython.lltypesystem.rstr import STR
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rtyper import RPythonTyper
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.tool.udir import udir

import py, sys

_compilation_info_ = ExternalCompilationInfo(
                         includes=['gdbm.h'],
                         libraries=['gdbm']
)

c_source = py.code.Source("""
     #include <string.h>

     char * fetch(GDBM_FILE name, datum key)
     {
         datum data;
         data = gdbm_fetch(name, key);

         return data.dptr;
     }
    """)

eci = ExternalCompilationInfo(
            includes=['gdbm.h'],
            libraries=['gdbm'],
            include_dirs=[udir],
            separate_module_sources=[c_source],
        )

datum = GcStruct('datum',('dptr',CCHARP), ('dsize', lltype.Signed))
err_func = lltype.Ptr(lltype.FuncType([], lltype.Void))
GDBM_FILE = rffi.COpaquePtr('GDBM_FILE', compilation_info=_compilation_info_)

open_gdbm = rffi.llexternal('gdbm_open', [CCHARP, INT, INT, INT, err_func], GDBM_FILE, compilation_info = _compilation_info_)
store_gdbm = rffi.llexternal('gdbm_store', [GDBM_FILE, datum, datum, INT], INT, compilation_info = _compilation_info_)
fetch_gdbm = rffi.llexternal('fetch', [GDBM_FILE, datum], CCHARP, compilation_info = eci)
close_gdbm = rffi.llexternal('gdbm_close', [GDBM_FILE], lltype.Void, compilation_info = _compilation_info_)

class GDBM(Wrappable):
    def __init__(self, space):
        self.space = space

    def gdbm_open(self, name, blocksize, read_write, mode):
        c_name = rffi.str2charp(name)
        self.struct_gdbm = open_gdbm(name, blocksize, read_write, mode,
lltype.nullptr(err_func.TO))

        if not self.struct_gdbm:
            return False

        return True

    def gdbm_store(self, key, content, flag):
        s = malloc(datum, zero=True)
        s.dptr = rffi.str2charp(key)
        s.dsize = len(key)

        s2 = malloc(datum, zero=True)
        s2.dptr = rffi.str2charp(content)
        s2.dsize = len(content)

        res_gdbm = store_gdbm(self.struct_gdbm, s, s2, flag)
        return self.space.wrap(res_gdbm)

    def gdbm_fetch(self, key):
        c_key = rffi.str2charp(key)
        a = malloc(datum, zero=True)
        a.dptr = rffi.str2charp(key)
        a.dsize = len(key)

        res = fetch_gdbm(self.struct_gdbm, a)
        str_res = rffi.charp2str(res)
        return self.space.wrap(str_res)

    def gdbm_close(self):
        close_gdbm(self.struct_gdbm)

def GDBM_new(space, w_subtype, initialdata= ''):
    w_gdbm = space.allocate_instance(GDBM, w_subtype)

    gdbm = space.interp_w(GDBM, w_gdbm)
    GDBM.__init__(gdbm, space)
    return w_gdbm


GDBM.typedef = TypeDef(
     'GDBMType',
     __new__  = interp2app(GDBM_new, unwrap_spec=[ObjSpace, W_Root, str]),
     open     = interp2app(GDBM.gdbm_open, unwrap_spec=['self', str, int, int, int]),
     store    = interp2app(GDBM.gdbm_store, unwrap_spec=['self', str, str, int]),
     fetch    = interp2app(GDBM.gdbm_fetch, unwrap_spec=['self', str]),
     close    = interp2app(GDBM.gdbm_close, unwrap_spec=['self'])
)
