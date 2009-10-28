import os
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.rarithmetic import r_uint, r_singlefloat
from pypy.rlib.rlog import AbstractLogWriter, SIZEOF_FLOAT
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.module.ll_os_environ import os_getenv
from pypy.rpython.module.ll_os import underscore_on_windows

os_write = rffi.llexternal(underscore_on_windows+'write',
                           [rffi.INT, rffi.CCHARP, rffi.SIZE_T],
                           rffi.SIZE_T)
os_open = rffi.llexternal(underscore_on_windows+'open',
                          [rffi.CCHARP, rffi.INT, rffi.MODE_T],
                          rffi.INT)

l_pypylog = rffi.str2charp('PYPYLOG')

# ____________________________________________________________
#
# Important: logging on lltype must not use the GC at all
#

class LLLogWriter(AbstractLogWriter):
    BUFSIZE = 8192

    fd = -1

    def ll_get_filename(self):
        return os_getenv(l_pypylog)

    def do_open_file(self):
        l_result = self.ll_get_filename()
        if l_result and l_result[0] != '\x00':
            if l_result[0] == '+':
                self.always_flush = True
                l_result = rffi.ptradd(l_result, 1)
            flags = rffi.cast(rffi.INT, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
            mode = rffi.cast(rffi.MODE_T, 0666)
            self.fd = rffi.cast(lltype.Signed, os_open(l_result, flags, mode))
        self.enabled = self.fd >= 0

    def do_write(self, fd, buf, size):
        if we_are_translated():
            os_write(rffi.cast(rffi.INT, fd),
                     buf,
                     rffi.cast(rffi.SIZE_T, size))
        else:
            l = [buf[i] for i in range(size)]
            s = ''.join(l)
            os.write(fd, s)
        self.writecount += 1

    def _register(self, rtyper):
        # register flush() to be called at program exit
        def flush_log_cache():
            if self.initialized_file:
                self._flush()
        annhelper = rtyper.getannmixlevel()
        annhelper.register_atexit(flush_log_cache)

    def create_buffer(self):
        self.buffer = lltype.malloc(rffi.CCHARP.TO, self.BUFSIZE, flavor='raw')
        self.buffer_position = 0
        self.writecount = 0

    def write_int(self, n):
        self._write_int_noflush(n)
        if self.buffer_position > self.BUFSIZE-48:
            self._flush()

    def _write_int_noflush(self, n):
        p = self.buffer_position
        buf = self.buffer
        n = r_uint(n)
        while n > 0x7F:
            buf[p] = chr((n & 0x7F) | 0x80)
            p += 1
            n >>= 7
        buf[p] = chr(n)
        self.buffer_position = p + 1

    def write_str(self, s):
        start = 0
        length = len(s)
        self._write_int_noflush(length)
        while self.buffer_position + length > self.BUFSIZE - 24:
            count = self.BUFSIZE - self.buffer_position
            if count > length:
                count = length
            self._write_raw_data(s, start, count)
            start += count
            length -= count
            self._flush()
        self._write_raw_data(s, start, length)

    def _write_raw_data(self, s, start, length):
        p = self.buffer_position
        buf = self.buffer
        i = 0
        while i < length:
            buf[p + i] = s[start + i]
            i += 1
        self.buffer_position = p + length

    def write_float(self, f):
        p = self.buffer_position
        ptr = rffi.cast(rffi.FLOATP, rffi.ptradd(self.buffer, p))
        ptr[0] = r_singlefloat(f)
        self.buffer_position = p + SIZEOF_FLOAT
        if self.buffer_position > self.BUFSIZE-48:
            self._flush()

    def _flush(self):
        if self.buffer_position > 0:
            self.do_write(self.fd, self.buffer, self.buffer_position)
        self.buffer_position = 0

    def _close(self):
        self._flush()
        os.close(self.fd)
