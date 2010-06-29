
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

