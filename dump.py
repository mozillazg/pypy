#! /usr/bin/env python
import struct

f = open('debug_memrecord', 'rb')
while 1:
    data = f.read(20)
    if len(data) < 20:
        break
    print '  %8x %8x %8x %8x %8x' % struct.unpack("iiiii", data)
f.close()
