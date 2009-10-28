import autopath
import struct, re, fnmatch
from pypy.rlib.rarithmetic import intmask
from pypy.rlib import rlog

SIZEOF_FLOAT = rlog.SIZEOF_FLOAT


class LogCategory(object):

    def __init__(self, category, message, index):
        self.category = category
        self.message = message
        self.index = index
        self.types = re.findall(r"%\(\w+\)(\w)", message)
        self.messagestr = re.sub(r"%\(\w+\)", "%", message)


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
                categories[index] = LogCategory(category, message, index)
            else:
                curtime += self.read_float()
                cat = categories[c]
                entries = [readers[t]() for t in cat.types]
                yield curtime, cat, entries


def parse_log(filename):
    logparser = LogParser(open(filename, 'rb'))
    return logparser.enum_entries()

def dump_log(filename, limit='*', highlight=False):
    for curtime, cat, entries in parse_log(filename):
        if not fnmatch.fnmatch(cat.category, limit):
            continue
        try:
            printcode = cat.printcode
        except AttributeError:
            code = '[%s] ' % cat.category
            message = cat.messagestr.replace('\n', '\n' + ' '*len(code))
            printcode = code + message
            if highlight:
                if cat.category.endswith('{'):
                    printcode = '\x1B[1m%s\x1B[0m' % (printcode,)
                elif cat.category.endswith('}'):
                    printcode = '\x1B[31m%s\x1B[0m' % (printcode,)
            cat.printcode = printcode
        print printcode % tuple(entries)

def extract_sections(filename, limit):
    """Extract sections between 'limit-{' and 'limit-}'.
    Yields multiline strings, each a complete section.
    Accept * and ? in 'limit'.
    """
    pieces = None
    for curtime, cat, entries in parse_log(filename):
        if fnmatch.fnmatch(cat.category, limit + '-{'):
            pieces = []
        if pieces is not None:
            pieces.append(cat.messagestr % tuple(entries))
            if fnmatch.fnmatch(cat.category, limit + '-}'):
                yield '\n'.join(pieces)
                pieces = None


if __name__ == '__main__':
    import sys
    filename = sys.argv[1]
    if len(sys.argv) > 2:
        limit = sys.argv[2] + '*'
    else:
        limit = '*'
    highlight = sys.stdout.isatty()
    dump_log(filename, limit, highlight)
