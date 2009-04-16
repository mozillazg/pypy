from pypy.interpreter import gateway

app = gateway.applevel(r'''
    def PyUnicode_DecodeUnicodeEscape(data):
        import _codecs
        return _codecs.unicode_escape_decode(data)[0]

    def PyUnicode_DecodeRawUnicodeEscape(data):
        import _codecs
        return _codecs.raw_unicode_escape_decode(data)[0]

    def PyUnicode_DecodeUTF8(data):
        import _codecs
        return _codecs.utf_8_decode(data)[0]

    def PyUnicode_AsEncodedString(data, encoding):
        import _codecs
        return _codecs.encode(data, encoding)
''')

PyUnicode_DecodeUnicodeEscape = app.interphook('PyUnicode_DecodeUnicodeEscape')
PyUnicode_DecodeRawUnicodeEscape = app.interphook('PyUnicode_DecodeRawUnicodeEscape')
PyUnicode_DecodeUTF8 = app.interphook('PyUnicode_DecodeUTF8')
PyUnicode_AsEncodedString = app.interphook('PyUnicode_AsEncodedString')
