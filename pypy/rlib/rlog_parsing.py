"""
Utilities to parse a log file.  When used from the command-line,
the syntax is:

   python rlog_parsing.py [-f|--follow] [-l|--limit=..] logfile

    -f, --follow      wait for file growth and display it too
    -l, --limit=CAT   only shows log entries of category 'CAT*'
                      (supports * and ? special characters)
"""
import autopath
import struct, re, fnmatch, time
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


class FollowFile(object):
    def __init__(self, f):
        self.tell = f.tell
        self.seek = f.seek
        self._read = f.read
    def read(self, size):
        buf = self._read(size)
        try:
            while len(buf) < size:
                time.sleep(1)
                buf += self._read(size - len(buf))
        except KeyboardInterrupt:
            sys.exit(0)
        return buf

def dump_log(filename, limit='*', highlight=False, follow=False):
    f = open(filename, 'rb')
    if follow:
        f = FollowFile(f)
    logparser = LogParser(f)
    for curtime, cat, entries in logparser.enum_entries():
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
    import sys, getopt
    options, args = getopt.gnu_getopt(sys.argv[1:], 'l:f',
                                      ['limit=', 'follow'])
    if len(args) != 1:
        print __doc__
        sys.exit(2)
    [filename] = args
    options = dict(options)
    limit = options.get('-l', options.get('--limit', '')) + '*'
    follow = '-f' in options or '--follow' in options
    highlight = sys.stdout.isatty()
    dump_log(filename, limit=limit, highlight=highlight, follow=follow)
