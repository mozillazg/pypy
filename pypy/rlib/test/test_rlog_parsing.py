import py, struct
from cStringIO import StringIO
from pypy.rlib.rlog_parsing import LogParser

def test_read_int_str():
    s = (chr(42) +
         chr(0x9A) + chr(15) +
         chr(3) + 'Abc' +
         chr(0x82) + chr(1) + 'x'*130 +
         chr(0))
    logparser = LogParser(StringIO(s), has_signature=False)
    x = logparser.read_int()
    assert x == 42
    x = logparser.read_int()
    assert x == (15 << 7) | 0x1A
    x = logparser.read_str()
    assert x == 'Abc'
    x = logparser.read_str()
    assert x == 'x'*130
    x = logparser.read_int()
    assert x == 0
    py.test.raises(EOFError, logparser.read_int)

def test_simple_parsing_int():
    s = ('\x00\x01\x02Aa\x0EHello %(foo)d.' +
         '\x01' + struct.pack("f", 12.5) + chr(42) +
         '\x01' + struct.pack("f", 2.5) + chr(61))
    logparser = LogParser(StringIO(s), has_signature=False)
    entries = list(logparser.enum_entries())
    assert len(entries) == 2
    cat = entries[0][1]
    assert entries == [
        (12.5, cat, [42]),
        (15.0, cat, [61]),
        ]

def test_simple_parsing_float():
    s = ('\x00\x82\x05\x02Aa\x0EHello %(foo)f.' +
         '\x82\x05' + struct.pack("ff", 12.5, -62.5) +
         '\x82\x05' + struct.pack("ff", 2.5, -0.25))
    logparser = LogParser(StringIO(s), has_signature=False)
    entries = list(logparser.enum_entries())
    assert len(entries) == 2
    cat = entries[0][1]
    assert entries == [
        (12.5, cat, [-62.5]),
        (15.0, cat, [-0.25]),
        ]
