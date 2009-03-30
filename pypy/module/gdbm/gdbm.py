from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.lltypesystem.rffi import *
from pypy.rpython.lltypesystem.lltype import Signed, Ptr, Char, malloc 
from pypy.rpython.lltypesystem.rstr import STR
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rtyper import RPythonTyper

import py
import sys

datum = GcStruct('datum',('dptr',CCHARP), ('dsize', lltype.Signed))

class Gdbm:
	def __init__(self):
		self.eci = ExternalCompilationInfo(includes=['gdbm.h'], libraries=['gdbm'])
		self.gdbm_file = CStructPtr( 'GDBM_FILE', ('dummy', INT))
		#self.struct_gdbm = lltype.malloc(self.gdbm_file.TO, flavor='raw')	

	def open(self, name, blocksize, read_write, mode):
		err_func = lltype.Ptr(lltype.FuncType([], lltype.Void))
		open_gdbm = rffi.llexternal('gdbm_open', [CCHARP, INT, INT, INT, err_func], self.gdbm_file, compilation_info=self.eci)
		self.struct_gdbm = open_gdbm(name, blocksize, read_write, mode, 0) 

	def fetch(self, dbf, key):
		fetch_gdbm = rffi.llexternal('gdbm_fetch', [self.gdbm_file, CCHARP], datum, compilation_info=self.eci)
		return fetch_gdbm(dbf, key)

	def close(self):
		close_gdbm = rffi.llexternal('gdbm_close', [self.gdbm_file], INT, compilation_info = self.eci)
		close_gdbm(self.struct_gdbm)

