# -*- coding: utf-8 -*-

import py
import sys
from pypy.interpreter.utf8 import (
    Utf8Str, Utf8Builder, utf8chr, utf8ord)
from rpython.rtyper.lltypesystem import rffi

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

def test_iterator():
    s = build_utf8str()
    iter = s.codepoint_iter()
    assert iter.peek_next() == 0x41
    assert list(iter) == [0x41, 0x10F, 0x20AC, 0x1F63D]

    for i in range(1, 5):
        iter = s.codepoint_iter()
        iter.move(i)
        if i != 4:
            assert iter.peek_next() == [0x41, 0x10F, 0x20AC, 0x1F63D][i]
        l = list(iter)
        assert l == [0x41, 0x10F, 0x20AC, 0x1F63D][i:]

    for i in range(1, 5):
        iter = s.codepoint_iter()
        list(iter) # move the iterator to the end
        iter.move(-i)
        l = list(iter)
        assert l == [0x41, 0x10F, 0x20AC, 0x1F63D][4-i:]

    iter = s.char_iter()
    l = [s.bytes.decode('utf8') for s in list(iter)]
    if sys.maxunicode < 65536:
        assert l[:3] == [u'A', u'\u010F', u'\u20AC']
    else:
        assert l == [u'A', u'\u010F', u'\u20AC', u'\U0001F63D']

def test_reverse_iterator():
    s = build_utf8str()
    iter = s.reverse_codepoint_iter()
    assert iter.peek_next() == 0x1F63D
    assert list(iter) == [0x1F63D, 0x20AC, 0x10F, 0x41]

    for i in range(1, 5):
        iter = s.reverse_codepoint_iter()
        iter.move(i)
        if i != 4:
            assert iter.peek_next() == [0x1F63D, 0x20AC, 0x10F, 0x41][i]
        l = list(iter)
        assert l == [0x1F63D, 0x20AC, 0x10F, 0x41][i:]

    for i in range(1, 5):
        iter = s.reverse_codepoint_iter()
        list(iter) # move the iterator to the end
        iter.move(-i)
        l = list(iter)
        assert l == [0x1F63D, 0x20AC, 0x10F, 0x41][4-i:]

def test_builder_append_slice():
    builder = Utf8Builder()
    builder.append_slice(Utf8Str.from_unicode(u"0ê0"), 1, 2)
    builder.append_slice("Test", 1, 3)

    assert builder.build() == u"êes"

def test_eq():
    assert Utf8Str('test') == Utf8Str('test')
    assert Utf8Str('test') != Utf8Str('test1')

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

    with py.test.raises(IndexError):
        c = s[4]

def test_getslice():
    s = build_utf8str()

    assert s[0:1] == u'A'
    assert s[0:2] == u'A\u010F'
    assert s[1:2] == u'\u010F'

def test_convert_indices():
    s = build_utf8str()

    assert s.index_of_char(0) == 0
    assert s.index_of_char(1) == 1
    assert s.index_of_char(2) == 3
    assert s.index_of_char(3) == 6

    for i in range(len(s)):
        assert s.char_index_of_byte(s.index_of_char(i)) == i

def test_join():
    s = Utf8Str(' ')
    assert s.join([]) == u''

    
    assert s.join([Utf8Str('one')]) == u'one'
    assert s.join([Utf8Str('one'), Utf8Str('two')]) == u'one two'

def test_find():
    u = u"äëïöü"
    s = Utf8Str.from_unicode(u)

    for c in u:
        assert s.find(Utf8Str.from_unicode(u)) == u.find(u)
        assert s.rfind(Utf8Str.from_unicode(u)) == u.rfind(u)

    assert s.find('') == u.find('')
    assert s.rfind('') == u.rfind('')

    assert s.find('1') == u.find('1')
    assert s.rfind('1') == u.rfind('1')

    assert Utf8Str.from_unicode(u'abcdefghiabc').rfind(u'') == 12

def test_count():
    u = u"12äëïöü223"
    s = Utf8Str.from_unicode(u)

    assert s.count("1") == u.count("1")
    assert s.count("2") == u.count("2")
    assert s.count(Utf8Str.from_unicode(u"ä")) == u.count(u"ä")

def test_split():
    # U+00A0 is a non-breaking space
    u = u"one two three\xA0four"
    s = Utf8Str.from_unicode(u)

    assert s.split() == u.split()
    assert s.split(' ') == u.split(' ')
    assert s.split(maxsplit=2) == u.split(None, 2)
    assert s.split(' ', 2) == u.split(' ', 2)
    assert s.split('\n') == [s]

def test_rsplit():
    # U+00A0 is a non-breaking space
    u = u"one two three\xA0four"
    s = Utf8Str.from_unicode(u)

    assert s.rsplit() == u.rsplit()
    assert s.rsplit(' ') == u.rsplit(' ')
    assert s.rsplit(maxsplit=2) == u.rsplit(None, 2)
    assert s.rsplit(' ', 2) == u.rsplit(' ', 2)
    assert s.rsplit('\n') == [s]

def test_copy_to_wcharp():
    s = build_utf8str()
    if sys.maxunicode < 0x10000 and rffi.sizeof(rffi.WCHAR_T) == 4:
        # The last character requires a surrogate pair on narrow builds and
        # so won't be converted correctly by rffi.wcharp2unicode
        s = s[:-1]

    wcharp = s.copy_to_wcharp()
    u = rffi.wcharp2unicode(wcharp)
    rffi.free_wcharp(wcharp)
    assert s == u

def test_from_wcharp():
    def check(u):
        wcharp = rffi.unicode2wcharp(u)
        s = Utf8Str.from_wcharp(wcharp)
        rffi.free_wcharp(wcharp)
        assert s == u
    check(u'A\u010F\u20AC\U0001F63D')
    check(u'0xDCC0 ')
    check(u'0xDCC0')

def test_from_wcharpn():
    u = u'A\u010F\u20AC\U0001F63D'
    wcharp = rffi.unicode2wcharp(u)
    s = Utf8Str.from_wcharpn(wcharp, 3)
    assert s == u[:3]

    s = Utf8Str.from_wcharpn(wcharp, 4)
    if sys.maxunicode == 0xFFFF:
        assert s == u[:4]
    else:
        assert s == u

    rffi.free_wcharp(wcharp)
