import py, time, struct
from pypy.tool.ansi_print import ansi_log
from pypy.rlib.unroll import unrolling_iterable
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
        translator = self.bookkeeper.annotator.translator
        if translator.config.translation.rlog:
            from pypy.annotation import model as annmodel
            return annmodel.s_Bool
        else:
            return self.bookkeeper.immutablevalue(False)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        translator = hop.rtyper.annotator.translator
        if translator.config.translation.rlog:
            from pypy.annotation import model as annmodel
            logwriter = get_logwriter(hop.rtyper)
            annhelper = hop.rtyper.getannmixlevel()
            c_func = annhelper.constfunc(logwriter.has_log, [],
                                         annmodel.s_Bool)
            hop.exception_cannot_occur()
            return hop.genop('direct_call', [c_func], resulttype=lltype.Bool)
        else:
            return hop.inputconst(lltype.Bool, False)


class DebugLogEntry(ExtRegistryEntry):
    _about_ = debug_log

    def compute_result_annotation(self, s_category, s_message, **kwds_s):
        from pypy.annotation import model as annmodel
        translator = self.bookkeeper.annotator.translator
        if translator.config.translation.rlog:
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
                cat = LogCategory(s_category.const, s_message.const, num)
                logcategories[s_category.const] = cat
            else:
                assert cat.message == s_message.const, (
                    "log category %r is used with different messages:\n\t%s\n"
                    "\t%s" % (s_category.const, cat.message, s_message.const))
            for entry, _ in cat.entries:
                name = 's_' + entry
                assert name in kwds_s, "missing log entry %r" % (entry,)
                del kwds_s[name]
            assert not kwds_s, "unexpected log entries %r" % (kwds_s.keys(),)
        return annmodel.s_None

    def specialize_call(self, hop, **kwds_i):
        from pypy.rpython.lltypesystem import lltype
        translator = hop.rtyper.annotator.translator
        if translator.config.translation.rlog:
            from pypy.annotation import model as annmodel
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
        # XXX detect lltype vs. ootype
        from pypy.rlib.rlog_ll import LLLogWriter
        logwriter = LLLogWriter()
        logwriter._register(rtyper)
        rtyper.annotator.translator._logwriter = logwriter
        return logwriter

# ____________________________________________________________

import re

r_entry = re.compile(r"%\((\w+)\)([sdf])")

SIZEOF_FLOAT = struct.calcsize("f")


class LogCategory(object):
    seen_by = None

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


class AbstractLogWriter(object):
    get_time = time.time

    def __init__(self):
        self.enabled = True
        self.initialized_file = False
        self.curtime = 0.0
        #
        def has_log():
            if not self.initialized_file:
                self.open_file()
            return self.enabled
        self.has_log = has_log

    def open_file(self):
        self.do_open_file()
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
    open_file._dont_inline_ = True

    def define_new_category(self, cat):
        if not self.initialized_file:
            self.open_file()
        # write the category definition line
        if self.enabled:
            self.write_int(0)
            self.write_int(cat.index)
            self.write_str(cat.category)
            self.write_str(cat.message)
            cat.seen_by = self
    define_new_category._dont_inline_ = True

    def add_entry(self, cat):
        if cat.seen_by is not self:
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
