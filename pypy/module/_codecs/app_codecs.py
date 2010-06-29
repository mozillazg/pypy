
"""

   _codecs -- Provides access to the codec registry and the builtin
              codecs.

   This module should never be imported directly. The standard library
   module "codecs" wraps this builtin module for use within Python.

   The codec registry is accessible via:

     register(search_function) -> None

     lookup(encoding) -> (encoder, decoder, stream_reader, stream_writer)

   The builtin Unicode codecs use the following interface:

     <encoding>_encode(Unicode_object[,errors='strict']) -> 
         (string object, bytes consumed)

     <encoding>_decode(char_buffer_obj[,errors='strict']) -> 
        (Unicode object, bytes consumed)

   <encoding>_encode() interfaces also accept non-Unicode object as
   input. The objects are then converted to Unicode using
   PyUnicode_FromObject() prior to applying the conversion.

   These <encoding>s are available: utf_8, unicode_escape,
   raw_unicode_escape, unicode_internal, latin_1, ascii (7-bit),
   mbcs (on win32).


Written by Marc-Andre Lemburg (mal@lemburg.com).

Copyright (c) Corporation for National Research Initiatives.

"""

def escape_encode( obj, errors='strict'):
    """None
    """
    s = repr(obj)
    v = s[1:-1]
    return v, len(v)

def unicode_internal_encode( obj, errors='strict'):
    """None
    """
    import sys
    if sys.maxunicode == 65535:
        unicode_bytes = 2
    else:
        unicode_bytes = 4
    p = []
    for x in obj:
        i = ord(x)
        bytes = []
        for j in xrange(unicode_bytes):
            bytes += chr(i%256)
            i >>= 8
        if sys.byteorder == "big":
            bytes.reverse()
        p += bytes
    res = ''.join(p)
    return res, len(res)

def unicode_internal_decode( unistr, errors='strict'):
    if type(unistr) == unicode:
        return unistr, len(unistr)
    else:
        import sys
        if sys.maxunicode == 65535:
            unicode_bytes = 2
        else:
            unicode_bytes = 4
        p = []
        i = 0
        if sys.byteorder == "big":
            start = unicode_bytes - 1
            stop = -1
            step = -1
        else:
            start = 0
            stop = unicode_bytes
            step = 1
        while i < len(unistr):
            if len(unistr) - i < unicode_bytes:
                msg = 'truncated input'
                next, i = unicode_call_errorhandler(errors, 'unicode_internal', msg,
                                                    unistr, i, len(unistr))
                p += next
                continue
            t = 0
            h = 0
            for j in range(start, stop, step):
                t += ord(unistr[i+j])<<(h*8)    
                h += 1
            i += unicode_bytes
            try:
                p += unichr(t)
            except ValueError:
                startpos = i - unicode_bytes
                endpos = i
                msg = "unichr(%s) not in range" % (t,)
                next, i = unicode_call_errorhandler(errors, 'unicode_internal', msg,
                                                    unistr, startpos, endpos)
                p += next
        res = u''.join(p)
        return res, len(unistr)

# XXX needs error messages when the input is invalid
def escape_decode(data, errors='strict'):
    """None
    """
    l = len(data)
    i = 0
    res = []
    while i < l:
        
        if data[i] == '\\':
            i += 1
            if i >= l:
                raise ValueError("Trailing \\ in string")
            else:
                if data[i] == '\\':
                    res += '\\'
                elif data[i] == 'n':
                    res += '\n'
                elif data[i] == 't':
                    res += '\t'
                elif data[i] == 'r':
                    res += '\r'
                elif data[i] == 'b':
                    res += '\b'
                elif data[i] == '\'':
                    res += '\''
                elif data[i] == '\"':
                    res += '\"'
                elif data[i] == 'f':
                    res += '\f'
                elif data[i] == 'a':
                    res += '\a'
                elif data[i] == 'v':
                    res += '\v'
                elif '0' <= data[i] <= '9':
                    # emulate a strange wrap-around behavior of CPython:
                    # \400 is the same as \000 because 0400 == 256
                    octal = data[i:i+3]
                    res += chr(int(octal, 8) & 0xFF)
                    i += 2
                elif data[i] == 'x':
                    hexa = data[i+1:i+3]
                    res += chr(int(hexa, 16))
                    i += 2
        else:
            res += data[i]
        i += 1
    res = ''.join(res)    
    return res, len(data)

#  ----------------------------------------------------------------------

def unicode_call_errorhandler(errors,  encoding, 
                reason, input, startinpos, endinpos, decode=True):
    
    import _codecs
    errorHandler = _codecs.lookup_error(errors)
    if decode:
        exceptionObject = UnicodeDecodeError(encoding, input, startinpos, endinpos, reason)
    else:
        exceptionObject = UnicodeEncodeError(encoding, input, startinpos, endinpos, reason)
    res = errorHandler(exceptionObject)
    if isinstance(res, tuple) and len(res) == 2 and isinstance(res[0], unicode) and isinstance(res[1], int):
        newpos = res[1]
        if (newpos < 0):
            newpos = len(input) + newpos
        if newpos < 0 or newpos > len(input):
            raise IndexError( "position %d from error handler out of bounds" % newpos)
        return res[0], newpos
    else:
        raise TypeError("encoding error handler must return (unicode, int) tuple, not %s" % repr(res))


def charmap_build(somestring):
    m = {}
    num = 0
    for elem in somestring:
        m[ord(elem)] = num
        num += 1
    return m

    
