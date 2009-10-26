from pypy.rlib import rlog
from pypy.tool.udir import udir


def test_log_direct():
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

def test_logwriter():
    class FakeCategory:
        def __init__(self, index, message):
            self.index = index
            self.message = message
    #
    logwriter = MyLogWriter()
    cat5 = FakeCategory(5, "foobar")
    cat7 = FakeCategory(7, "baz")
    logwriter.add_entry(cat5)
    logwriter.add_entry(cat5)
    logwriter.add_entry(cat7)
    logwriter.add_entry(cat5)
    #
    assert logwriter.content == [
        ord('R'), ord('L'), ord('o'), ord('g'), ord('\n'),
        0, 5, "foobar",
        5,
        5,
        0, 7, "baz",
        7,
        5]

def test_logcategory_call():
    message = "abc%(foo)ddef%(bar)sghi"
    cat = rlog.LogCategory("Aa", message, 17)
    logwriter = MyLogWriter()
    call = cat.get_call(logwriter)
    call(515, "hellooo")
    call(2873, "woooooorld")
    #
    assert logwriter.content == [
        ord('R'), ord('L'), ord('o'), ord('g'), ord('\n'),
        0, 17, message,
        17, 515, "hellooo",
        17, 2873, "woooooorld"]
