#! /usr/bin/env python
import struct, os

f = os.popen('zcat debug_memrecord.gz', 'r')
while 1:
    data = f.read(20)
    if len(data) < 20:
        break
    print '  %8x  %8x  %8x  %8x  %8x' % struct.unpack("IIIII", data)
f.close()
