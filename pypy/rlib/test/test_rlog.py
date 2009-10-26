import struct, os
from pypy.rlib import rlog, rlog_parsing
from pypy.rlib.rarithmetic import intmask
from pypy.tool.udir import udir
from pypy.rpython.test.test_llinterp import interpret


def test_log_direct():
    # this should produce some output via py.log...
    rlog.debug_log("Aa", "hello %(foo)d %(bar)d", foo=5, bar=7)
    # let's replace py.log with our own class to check
    messages = []
    class MyLog:
        def Aa(self, msg):
            messages.append(msg)
    previous = rlog._log
    try:
        rlog._log = MyLog()
        rlog.debug_log("Aa", "hello %(foo)d %(bar)d", foo=5, bar=7)
        assert messages == ["hello 5 7"]
    finally:
        rlog._log = previous

def test_logcategory():
    message = "abc%(foo)ddef%(bar)sghi"
    cat = rlog.LogCategory("Aa", message, 17)
    assert cat.category == "Aa"
    assert cat.message == message
    assert cat.index == 17
    assert cat.entries == [('foo', 'd'), ('bar', 's')]


class MyLogWriter(rlog.AbstractLogWriter):
    _path = udir.join('test_rlog.logwriter')

    def get_time(self):
        return 123.0
    def get_filename(self):
        return str(self._path)
    def create_buffer(self):
        self.content = []
    def write_int(self, n):
        assert isinstance(n, int)
        self.content.append(n)
    def write_str(self, s):
        assert isinstance(s, str)
        self.content.append(s)
    def write_float(self, f):
        assert isinstance(f, float)
        self.content.append(f)

def test_logwriter():
    class FakeCategory:
        def __init__(self, index, category, message):
            self.index = index
            self.category = category
            self.message = message
    #
    logwriter = MyLogWriter()
    cat5 = FakeCategory(5, "F5", "foobar")
    cat7 = FakeCategory(7, "F7", "baz")
    logwriter.add_entry(cat5)
    logwriter.add_entry(cat5)
    logwriter.add_entry(cat7)
    logwriter.add_entry(cat5)
    #
    assert logwriter.content == [
        ord('R'), ord('L'), ord('o'), ord('g'), ord('\n'), -1, 1.0,
        0, 5, "F5", "foobar",
        5, 123.0,
        5, 0.0,
        0, 7, "F7", "baz",
        7, 0.0,
        5, 0.0]

def test_logcategory_call():
    from pypy.rpython.annlowlevel import llstr
    message = "abc%(foo)ddef%(bar)sghi"
    cat = rlog.LogCategory("Aa", message, 17)
    logwriter = MyLogWriter()
    call = cat.gen_call(logwriter)
    call(515, llstr("hellooo"))
    call(2873, llstr("woooooorld"))
    #
    assert logwriter.content == [
        ord('R'), ord('L'), ord('o'), ord('g'), ord('\n'), -1, 1.0,
        0, 17, "Aa", message,
        17, 123.0, 515, "hellooo",
        17, 0.0, 2873, "woooooorld"]


SIZEOF_FLOAT = rlog.LLLogWriter.SIZEOF_FLOAT

class TestLLLogWriter:
    COUNTER = 0

    def open(self):
        path = udir.join('test_rlog.lllogwriter%d' % TestLLLogWriter.COUNTER)
        self.path = path
        TestLLLogWriter.COUNTER += 1
        #
        class MyLLLogWriter(rlog.LLLogWriter):
            def get_filename(self):
                return str(path)
        #
        logwriter = MyLLLogWriter()
        logwriter.open_file()
        return logwriter

    def read_uint(self, f):
        shift = 0
        result = 0
        lastbyte = ord(f.read(1))
        while lastbyte & 0x80:
            result |= ((lastbyte & 0x7F) << shift)
            shift += 7
            lastbyte = ord(f.read(1))
        result |= (lastbyte << shift)
        return result

    def read_float(self, f):
        return struct.unpack("f", f.read(SIZEOF_FLOAT))[0]

    def check(self, expected):
        f = self.path.open('rb')
        f.seek(0, 2)
        totalsize = f.tell()
        f.seek(0, 0)
        header = f.read(5)
        assert header == 'RLog\n'
        for expect in [-1, 1.0] + expected:
            if isinstance(expect, int):
                result = self.read_uint(f)
                assert intmask(result) == expect
            elif isinstance(expect, str):
                length = self.read_uint(f)
                assert length < totalsize
                got = f.read(length)
                assert got == expect
            elif isinstance(expect, float):
                result = self.read_float(f)
                assert abs(result - expect) < 1E-6
            else:
                assert 0, expect
        moredata = f.read(10)
        assert not moredata

    def test_write_int(self):
        logwriter = self.open()
        for i in range(logwriter.BUFSIZE):
            logwriter.write_int(i)
        logwriter._close()
        self.check(range(logwriter.BUFSIZE))
        assert logwriter.writecount <= 3

    def test_write_str(self):
        logwriter = self.open()
        slist = map(str, range(logwriter.BUFSIZE))
        for s in slist:
            logwriter.write_str(s)
        logwriter._close()
        self.check(slist)
        assert logwriter.writecount <= 14

    def test_write_mixed(self):
        logwriter = self.open()
        xlist = []
        for i in range(logwriter.BUFSIZE):
            if i & 1:
                i = str(i)
            xlist.append(i)
        for x in xlist:
            if isinstance(x, int):
                logwriter.write_int(x)
            else:
                logwriter.write_str(x)
        logwriter._close()
        self.check(xlist)
        assert logwriter.writecount <= 7

    def test_write_long_str(self):
        logwriter = self.open()
        slist = ['abcdefg' * n for n in [10, 100, 1000, 10000]]
        for s in slist:
            logwriter.write_str(s)
        logwriter._close()
        self.check(slist)
        assert logwriter.writecount <= 9

    def test_write_float(self):
        import math
        logwriter = self.open()
        flist = [math.log(x+0.1) for x in range(logwriter.BUFSIZE)]
        for f in flist:
            logwriter.write_float(f)
        logwriter._close()
        self.check(flist)
        assert logwriter.writecount <= 6


class roughly(float):
    def __eq__(self, other):
        return abs(self - other) < 1E-6
    def __ne__(self, other):
        return not self.__eq__(other)


class TestCompiled:
    COUNTER = 0

    def f(x):
        rlog.debug_log("Aa", "hello %(foo)d %(bar)f", foo=x, bar=-7.3)
        rlog.debug_log("Aa", "hello %(foo)d %(bar)f", foo=x+1, bar=x+0.5)
        rlog.debug_log("Ab", "<<%(baz)s>>", baz="hi there")

    def setup_method(self, _):
        self.old_pypylog = os.environ.get('PYPYLOG')
        self.pypylog = str(udir.join('test_rlog.TestCompiled%d' %
                                     TestCompiled.COUNTER))
        TestCompiled.COUNTER += 1
        os.environ['PYPYLOG'] = self.pypylog

    def teardown_method(self, _):
        if self.old_pypylog is None:
            del os.environ['PYPYLOG']
        else:
            os.environ['PYPYLOG'] = self.old_pypylog

    def check_result(self):
        entries = list(rlog_parsing.parse_log(self.pypylog))
        assert len(entries) == 3
        #
        assert isinstance(entries[0][0], float)
        assert isinstance(entries[1][0], float)
        assert isinstance(entries[2][0], float)
        #
        Aa = entries[0][1]
        Ab = entries[2][1]
        assert entries[1][1] is Aa
        assert Aa.category == 'Aa'
        assert Aa.message == 'hello %(foo)d %(bar)f'
        assert Aa.entries == [('foo', 'd'), ('bar', 'f')]
        assert Ab.category == 'Ab'
        assert Ab.message == '<<%(baz)s>>'
        assert Ab.entries == [('baz', 's')]
        #
        assert entries[0][2] == [132, roughly(-7.3)]
        assert entries[1][2] == [133, 132.5]
        assert entries[2][2] == ['hi there']

    def test_interpret(self):
        interpret(self.f.im_func, [132], malloc_check=False)
        self.check_result()
