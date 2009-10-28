import autopath
import struct
from pypy.rlib.rarithmetic import intmask
from pypy.rlib import rlog

SIZEOF_FLOAT = rlog.SIZEOF_FLOAT


class LogParser(object):

    def __init__(self, file, has_signature=True):
        self.f = file
        if has_signature:
            signature = self.f.read(5)
            assert signature == 'RLog\n'
            extra1 = self.read_int()
            assert extra1 == -1
            extra2 = self.read_float()
            assert extra2 == 1.0
        self.startpos = self.f.tell()

    def read_int(self):
        nextc = self.f.read(1)
        if not nextc:
            raise EOFError
        lastbyte = ord(nextc)
        if lastbyte < 0x80:
            return lastbyte
        shift = 0
        result = 0
        while lastbyte & 0x80:
            result |= ((lastbyte & 0x7F) << shift)
            shift += 7
            lastbyte = ord(self.f.read(1))
        result |= (lastbyte << shift)
        return intmask(result)

    def read_str(self):
        length = self.read_int()
        assert length >= 0
        return self.f.read(length)

    def read_float(self):
        return struct.unpack("f", self.f.read(SIZEOF_FLOAT))[0]

    def enum_entries(self):
        self.f.seek(self.startpos)
        categories = {}
        readers = {
            'd': self.read_int,
            's': self.read_str,
            'r': self.read_str,
            'f': self.read_float,
            }
        curtime = 0.0
        while 1:
            try:
                c = self.read_int()
            except EOFError:
                return
            if c == 0:
                # define_new_category
                index = self.read_int()
                category = self.read_str()
                message = self.read_str()
                assert index not in categories
                categories[index] = rlog.LogCategory(category, message, index)
            else:
                curtime += self.read_float()
                cat = categories[c]
                entries = [readers[t]() for t in cat.types]
                yield curtime, cat, entries


def parse_log(filename):
    logparser = LogParser(open(filename, 'rb'))
    return logparser.enum_entries()


if __name__ == '__main__':
    import sys, re
    r_replace = re.compile(r"%\(\w+\)")
    for curtime, cat, entries in parse_log(sys.argv[1]):
        try:
            printcode = cat.printcode
        except AttributeError:
            code = '[%s] ' % cat.category
            message = cat.message.replace('\n', '\n' + ' '*len(code))
            message = r_replace.sub("%", message)
            printcode = cat.printcode = code + message
        print printcode % tuple(entries)
