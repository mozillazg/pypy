import py, os, time
from pypy.tool.ansi_print import ansi_log
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.extregistry import ExtRegistryEntry

_log = py.log.Producer("rlog") 
py.log.setconsumer("rlog", ansi_log) 

# ____________________________________________________________


def debug_log(_category, _message, **_kwds):
    getattr(_log, _category)(_message % _kwds)

# ____________________________________________________________


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
        from pypy.rpython.lltypesystem import lltype
        translator = self.bookkeeper.annotator.translator
        logcategories = translator._logcategories
        cat = logcategories[hop.args_s[0].const]
        args_v = []
        for name, typechar in cat.entries:
            assert typechar == 'd'
            args_v.append(hop.inputarg(lltype.Signed, arg=kwds_i[name]))
        hop.exception_cannot_occur()
        hop.gendirectcall(cat.call, *args_v)

# ____________________________________________________________

import re

r_entry = re.compile(r"%\((\w+)\)([sd])")


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

    def get_call(self, logwriter):
        types = [typechar for name, typechar in self.entries]
        types = unrolling_iterable(types)
        #
        def call(*args):
            if logwriter.enabled:
                logwriter.add_entry(self)
                i = 0
                for typechar in types:
                    methname = 'add_subentry_' + typechar
                    getattr(logwriter, methname)(args[i])
                    i = i + 1
        call._always_inline_ = True
        return call

    def _freeze_(self):
        return True


class AbstractLogWriter(object):
    BUFSIZE = 8192

    def __init__(self):
        self.enabled = True
        self.initialized_file = False
        self.initialized_index = {}
        self.fd = -1

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
        self.initialized_file = True

    def define_new_category(self, cat):
        if not self.initialized_file:
            self.open_file()
        # write the category definition line
        if self.enabled:
            self.write_int(0)
            self.write_int(cat.index)
            self.write_str(cat.message)
        self.initialized_index[cat.index] = None

    def add_entry(self, cat):
        if cat.index not in self.initialized_index:
            self.define_new_category(cat)
        if self.enabled:
            self.write_int(cat.index)
    add_entry._dont_inline_ = True

    def add_subentry_d(self, num):
        if self.enabled:
            self.write_int(num)
    add_subentry_d._dont_inline_ = True

    def add_subentry_s(self, str):
        if self.enabled:
            self.write_str(str)
    add_subentry_d._dont_inline_ = True


class LLLogWriter(AbstractLogWriter):

    def create_buffer(self):
        self.buffer = lltype.malloc(rffi.CCHARP.TO, LogWriter.BUFSIZE,
                                    flavor='raw')
        self.buffer_position = 0

    def write_int(self, n):
        yyy

    def write_str(self, s):
        zzz

    def flush(self):
        if self.initialized_file:
            xxx
