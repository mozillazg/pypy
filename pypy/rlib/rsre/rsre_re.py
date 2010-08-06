import re, sys
from pypy.rlib.rsre import rsre_core, rsre_char
from pypy.rlib.rsre.test.test_match import get_code as _get_code
from pypy.module.unicodedata import unicodedb_3_2_0
rsre_char.unicodedb = unicodedb_3_2_0


I = IGNORECASE = 2   # ignore case
L = LOCALE     = 4   # assume current 8-bit locale
U = UNICODE    = 32  # assume unicode locale
M = MULTILINE  = 8   # make anchors look for newline
S = DOTALL     = 16  # make dot match newline
X = VERBOSE    = 64  # ignore whitespace and comments


def match(pattern, string, flags=0):
    return compile(pattern, flags).match(string)

def search(pattern, string, flags=0):
    return compile(pattern, flags).search(string)

def findall(pattern, string, flags=0):
    return compile(pattern, flags).findall(string)

def finditer(pattern, string, flags=0):
    return compile(pattern, flags).finditer(string)

def compile(pattern, flags=0):
    code, flags, args = _get_code(pattern, flags, allargs=True)
    return RSREPattern(pattern, code, flags, *args)

escape = re.escape
error = re.error


class RSREPattern(object):

    def __init__(self, pattern, code, flags,
                 num_groups, groupindex, indexgroup):
        self._code = code
        self.pattern = pattern
        self.flags = flags
        self.groups = num_groups
        self.groupindex = groupindex
        self._indexgroup = indexgroup

    def match(self, string, pos=0, endpos=sys.maxint):
        return self._make_match(rsre_core.match(self._code, string,
                                                pos, endpos,
                                                flags=self.flags))

    def search(self, string, pos=0, endpos=sys.maxint):
        return self._make_match(rsre_core.search(self._code, string,
                                                 pos, endpos,
                                                 flags=self.flags))

    def findall(self, string):
        matchlist = []
        for match in self.finditer(string):
            if self.groups == 0 or self.groups == 1:
                item = match.group(self.groups)
            else:
                item = match.groups("")
            matchlist.append(item)
        return matchlist        

    def finditer(self, string):
        matchlist = []
        start = 0
        while True:
            match = rsre_core.search(self._code, string, start,
                                     flags=self.flags)
            if match is None:
                break
            end = match.match_end
            yield RSREMatch(self, match)
            if start == end:
                start += 1
                if start > len(string):
                    break
            else:
                start = end

    def _make_match(self, res):
        if res is None:
            return None
        return RSREMatch(self, res)


class RSREMatch(object):

    def __init__(self, pattern, ctx):
        self.re = pattern
        self._ctx = ctx

    def span(self, groupnum=0):
        if not isinstance(groupnum, (int, long)):
            groupnum = self.re.groupindex[groupnum]
        return self._ctx.span(groupnum)

    def start(self, groupnum=0):
        return self.span(groupnum)[0]

    def end(self, groupnum=0):
        return self.span(groupnum)[1]

    def group(self, *groups):
        groups = groups or (0,)
        result = []
        for group in groups:
            frm, to = self.span(group)
            if 0 <= frm <= to:
                result.append(self._ctx._string[frm:to])
            else:
                result.append(None)
        if len(result) > 1:
            return tuple(result)
        else:
            return result[0]

    def groups(self, default=None):
        fmarks = self._ctx.flatten_marks()
        grps = []
        for i in range(1, self.re.groups+1):
            grp = self.group(i)
            if grp is None: grp = default
            grps.append(grp)
        return tuple(grps)

    def groupdict(self, default=None):
        d = {}
        for key, value in self.re.groupindex.iteritems():
            grp = self.group(value)
            if grp is None: grp = default
            d[key] = grp
        return d

    def expand(self, template):
        return re._expand(self.re, self, template)

    @property
    def regs(self):
        fmarks = self._ctx.flatten_marks()
        return tuple([(fmarks[i], fmarks[i+1])
                      for i in range(0, len(fmarks), 2)])

    @property
    def lastindex(self):
        self._ctx.flatten_marks()
        if self._ctx.match_lastindex < 0:
            return None
        return self._ctx.match_lastindex // 2 + 1

    @property
    def lastgroup(self):
        lastindex = self.lastindex
        if lastindex < 0 or lastindex >= len(self.re._indexgroup):
            return None
        return self.re._indexgroup[lastindex]

    @property
    def string(self):
        return self._ctx._string

    @property
    def pos(self):
        return self._ctx.match_start

    @property
    def endpos(self):
        return self._ctx.end
