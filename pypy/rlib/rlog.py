import py, os, time, struct
from pypy.tool.ansi_print import ansi_log
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import r_uint, r_singlefloat
from pypy.rlib.objectmodel import we_are_translated
from pypy.tool.sourcetools import func_with_new_name
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.annlowlevel import hlstr

_log = py.log.Producer("rlog") 
py.log.setconsumer("rlog", ansi_log) 

# ____________________________________________________________


def has_log():
    return True

def debug_log(_category, _message, **_kwds):
    getattr(_log, _category)(_message % _kwds)

# ____________________________________________________________


class HasLogEntry(ExtRegistryEntry):
    _about_ = has_log

    def compute_result_annotation(self):
        from pypy.annotation import model as annmodel
        return annmodel.s_Bool

    def specialize_call(self, hop):
        from pypy.annotation import model as annmodel
        from pypy.rpython.lltypesystem import lltype
        logwriter = get_logwriter(hop.rtyper)
        annhelper = hop.rtyper.getannmixlevel()
        c_func = annhelper.constfunc(logwriter.has_log, [],
                                     annmodel.s_Bool)
        hop.exception_cannot_occur()
        return hop.genop('direct_call', [c_func], resulttype=lltype.Bool)


class DebugLogEntry(ExtRegistryEntry):
    _about_ = debug_log

    def compute_result_annotation(self, s_category, s_message, **kwds_s):
        from pypy.annotation import model as annmodel
        assert s_category.is_constant()
        assert s_message.is_constant()
        translator = self.bookkeeper.annotator.translator
        try:
            logcategories = translator._logcategories
        except AttributeError:
            logcategories = translator._logcategories = {}
        try:
            cat = logcategories[s_category.const]
        except KeyError:
            num = len(logcategories) + 1
            logcategories[s_category.const] = LogCategory(s_category.const,
                                                          s_message.const,
                                                          num)
        else:
            assert cat.message == s_message.const, (
                "log category %r is used with different messages:\n\t%s\n\t%s"
                % (s_category.const, cat.message, s_message.const))
        return annmodel.s_None

    def specialize_call(self, hop, **kwds_i):
        from pypy.annotation import model as annmodel
        from pypy.rpython.lltypesystem import lltype
        logwriter = get_logwriter(hop.rtyper)
        translator = hop.rtyper.annotator.translator
        cat = translator._logcategories[hop.args_s[0].const]
        ann = {
            'd': annmodel.SomeInteger(),
            'f': annmodel.SomeFloat(),
            's': annmodel.SomeString(can_be_None=True),
            }
        annhelper = hop.rtyper.getannmixlevel()
        args_s = [ann[t] for t in cat.types]
        c_func = annhelper.constfunc(cat.gen_call(logwriter), args_s,
                                     annmodel.s_None)
        args_v = [c_func]
        for name, typechar in cat.entries:
            arg = kwds_i['i_'+name]
            if typechar == 'd':
                v = hop.inputarg(lltype.Signed, arg=arg)
            elif typechar == 'f':
                v = hop.inputarg(lltype.Float, arg=arg)
            elif typechar == 's':
                v = hop.inputarg(hop.rtyper.type_system.rstr.string_repr,
                                 arg=arg)
            else:
                assert 0, typechar
            args_v.append(v)
        hop.exception_cannot_occur()
        hop.genop('direct_call', args_v)
        return hop.inputconst(lltype.Void, None)

def get_logwriter(rtyper):
    try:
        return rtyper.annotator.translator._logwriter
    except AttributeError:
        logwriter = LLLogWriter()
        logwriter._register(rtyper)
        rtyper.annotator.translator._logwriter = logwriter
        return logwriter

# ____________________________________________________________

import re

r_entry = re.compile(r"%\((\w+)\)([sdf])")


class LogCategory(object):

    def __init__(self, category, message, index):
        self.category = category
        self.message = message
        self.index = index
        self.entries = []
        seen = {}
        for (name, typechar) in r_entry.findall(message):
            assert name not in seen, (
                "duplicate name %r in the log message %r" % (name, message))
            seen[name] = True
            self.entries.append((name, typechar))
        self.types = [typechar for name, typechar in self.entries]
        self.call = None

    def gen_call(self, logwriter):
        if self.call is None:
            self.logwriter = logwriter
            types = unrolling_iterable(self.types)
            #
            def call(*args):
                if not logwriter.enabled:
                    return
                if not logwriter.add_entry(self):
                    return
                i = 0
                for typechar in types:
                    methname = 'add_subentry_' + typechar
                    getattr(logwriter, methname)(args[i])
                    i = i + 1
            call = func_with_new_name(call, 'debug_log_' + self.category)
            call._always_inline_ = True
            self.call = call
        else:
            assert self.logwriter is logwriter
        return self.call

    def _freeze_(self):
        return True


class AbstractLogWriter(object):
    get_time = time.time

    def __init__(self):
        self.enabled = True
        self.initialized_file = False
        self.initialized_index = {}
        self.fd = -1
        self.curtime = 0.0
        #
        def has_log():
            if not self.initialized_file:
                self.open_file()
            return self.enabled
        self.has_log = has_log

    def get_filename(self):
        return os.environ.get('PYPYLOG')

    def open_file(self):
        from pypy.rpython.lltypesystem import lltype, rffi
        filename = self.get_filename()
        if filename:
            self.fd = os.open(filename,
                              os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                              0666)
        self.enabled = self.fd >= 0
        # write the header
        if self.enabled:
            self.create_buffer()
            for c in 'RLog\n':
                self.write_int(ord(c))
            # Write two numbers at the start, to ensure that the log is
            # considered invalid on machines with different endianness
            # or word size.  They also play the role of version numbers.
            self.write_int(-1)
            self.write_float(1.0)
        self.initialized_file = True

    def define_new_category(self, cat):
        if not self.initialized_file:
            self.open_file()
        # write the category definition line
        if self.enabled:
            self.write_int(0)
            self.write_int(cat.index)
            self.write_str(cat.category)
            self.write_str(cat.message)
            self.initialized_index[cat.index] = None

    def add_entry(self, cat):
        if cat.index not in self.initialized_index:
            self.define_new_category(cat)
            if not self.enabled:
                return False
        now = self.get_time()
        timestamp_delta = now - self.curtime
        self.curtime = now
        self.write_int(cat.index)
        self.write_float(timestamp_delta)
        # NB. we store the time delta since the previous log entry to get a
        # good precision even though it's encoded as a 4-bytes 'C float'
        return True

    def add_subentry_d(self, num):
        self.write_int(num)

    def add_subentry_s(self, llstr):
        if llstr:
            s = hlstr(llstr)
        else:
            s = '(null)'
        self.write_str(s)

    def add_subentry_f(self, float):
        self.write_float(float)

# ____________________________________________________________


class LLLogWriter(AbstractLogWriter):
    BUFSIZE = 8192
    SIZEOF_FLOAT = struct.calcsize("f")

    def do_write(self, fd, buf, size):
        if we_are_translated():
            from pypy.rpython.lltypesystem import rffi
            self._os_write(rffi.cast(rffi.INT, fd),
                           buf,
                           rffi.cast(rffi.SIZE_T, size))
        else:
            l = [buf[i] for i in range(size)]
            s = ''.join(l)
            os.write(fd, s)
        self.writecount += 1

    def _register(self, rtyper):
        from pypy.rpython.lltypesystem import rffi
        from pypy.rpython.module.ll_os import underscore_on_windows
        self._os_write = rffi.llexternal(underscore_on_windows+'write',
                                         [rffi.INT, rffi.CCHARP, rffi.SIZE_T],
                                         rffi.SIZE_T)
        # register flush() to be called at program exit
        def flush_log_cache():
            if self.initialized_file:
                self._flush()
        annhelper = rtyper.getannmixlevel()
        annhelper.register_atexit(flush_log_cache)

    def create_buffer(self):
        from pypy.rpython.lltypesystem import lltype, rffi
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
        self._write_int_noflush(len(s))
        p = self.buffer_position
        if p + len(s) > self.BUFSIZE-24:
            self._flush()
            os.write(self.fd, s)
            self.writecount += 1
        else:
            buf = self.buffer
            for i in range(len(s)):
                buf[p + i] = s[i]
            self.buffer_position = p + len(s)

    def write_float(self, f):
        from pypy.rpython.lltypesystem import rffi
        p = self.buffer_position
        ptr = rffi.cast(rffi.FLOATP, rffi.ptradd(self.buffer, p))
        ptr[0] = r_singlefloat(f)
        self.buffer_position = p + self.SIZEOF_FLOAT
        if self.buffer_position > self.BUFSIZE-48:
            self._flush()

    def _flush(self):
        if self.buffer_position > 0:
            self.do_write(self.fd, self.buffer, self.buffer_position)
        self.buffer_position = 0

    def _close(self):
        self._flush()
        os.close(self.fd)
