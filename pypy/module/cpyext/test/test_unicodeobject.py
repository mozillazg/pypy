# encoding: iso-8859-15
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.unicodeobject import Py_UNICODE
from pypy.rpython.lltypesystem import rffi, lltype

class TestUnicode(BaseApiTest):
    def test_unicodeobject(self, space, api):
        assert api.PyUnicode_GET_SIZE(space.wrap(u'späm')) == 4
        unichar = rffi.sizeof(Py_UNICODE)
        assert api.PyUnicode_GET_DATA_SIZE(space.wrap(u'späm')) == 4 * unichar

    def test_AS_DATA(self, space, api):
        word = space.wrap(u'spam')
        array = rffi.cast(rffi.CWCHARP, api.PyUnicode_AS_DATA(word))
        for (i, char) in enumerate(space.unwrap(word)):
            assert array[i] == char

    def test_IS(self, space, api):
        for char in [0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x1c, 0x1d, 0x1e, 0x1f,
                     0x20, 0x85, 0xa0, 0x1680, 0x2000, 0x2001, 0x2002,
                     0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008,
                     0x2009, 0x200a,
                     #0x200b is in Other_Default_Ignorable_Code_Point in 4.1.0
                     0x2028, 0x2029, 0x202f, 0x205f, 0x3000]:
            assert api.Py_UNICODE_ISSPACE(char)
        assert not api.Py_UNICODE_ISSPACE(ord(u'a'))

        assert api.Py_UNICODE_ISDECIMAL(ord(u'\u0660'))
        assert not api.Py_UNICODE_ISDECIMAL(ord(u'a'))

        for char in [0x0a, 0x0d, 0x1c, 0x1d, 0x1e, 0x85, 0x2028, 0x2029]:
            assert api.Py_UNICODE_ISLINEBREAK(char)

        assert api.Py_UNICODE_ISLOWER(ord(u'ä'))
        assert not api.Py_UNICODE_ISUPPER(ord(u'ä'))
        assert api.Py_UNICODE_ISLOWER(ord(u'a'))
        assert not api.Py_UNICODE_ISUPPER(ord(u'a'))
        assert not api.Py_UNICODE_ISLOWER(ord(u'Ä'))
        assert api.Py_UNICODE_ISUPPER(ord(u'Ä'))

    def test_TOLOWER(self, space, api):
        assert api.Py_UNICODE_TOLOWER(ord(u'ä')) == ord(u'ä')
        assert api.Py_UNICODE_TOLOWER(ord(u'Ä')) == ord(u'ä')

