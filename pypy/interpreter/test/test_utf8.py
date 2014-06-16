from pypy.interpreter.utf8 import (
    Utf8Str, Utf8Builder, utf8chr, utf8ord)

def build_utf8str():
    builder = Utf8Builder()
    builder.append('A') #0x41
    builder.append(0x10F) #0xC4 0x8F
    builder.append(0x20AC) #0xE2 0x82 0xAC
    builder.append(0x1F63D) #0xF0 0x9F 0x98 0xBD
    return builder.build()

def test_builder():
    s = build_utf8str()
    assert not s._is_ascii

    assert list(s.bytes) == [chr(i) for i in [
                                0x41,
                                0xC4, 0x8F,
                                0xE2, 0x82, 0xAC,
                                0xF0, 0x9F, 0x98, 0xBD,
                            ]]

def test_unicode_literal_comparison():
    builder = Utf8Builder()
    builder.append(0x10F)
    s = builder.build()
    assert s == u'\u010F'
    assert s[0] == u'\u010F'
    assert s[0] == utf8chr(0x10F)

def test_utf8chr():
    assert utf8chr(65) == u'A'
    assert utf8chr(0x7FF) == u'\u07FF'
    assert utf8chr(0x17FF) == u'\u17FF'
    assert utf8chr(0x10001) == u'\U00010001'

def test_utf8ord():
    s = build_utf8str()
    assert utf8ord(s) == 65
    assert utf8ord(s, 1) == 0x10F
    assert utf8ord(s, 2) == 0x20AC
    assert utf8ord(s, 3) == 0x1F63D

def test_len():
    s = build_utf8str()
    assert len(s) == 4

def test_getitem():
    s = build_utf8str()

    assert s[0] == utf8chr(65)
    assert s[1] == utf8chr(0x10F)
    assert s[2] == utf8chr(0x20AC)
    assert s[3] == utf8chr(0x1F63D)
    assert s[-1] == utf8chr(0x1F63D)
    assert s[-2] == utf8chr(0x20AC)

def test_getslice():
    s = build_utf8str()

    assert s[0:1] == u'A'
    assert s[0:2] == u'A\u010F'
    assert s[1:2] == u'\u010F'
    assert s[-4:-3] == u'A'
    assert s[-4:-2] == u'A\u010F'
