# NOT_RPYTHON
"""
A pure Python reimplementation of the _sre module from CPython 2.4
Copyright 2005 Nik Haldimann, licensed under the MIT license

This code is based on material licensed under CNRI's Python 1.6 license and
copyrighted by: Copyright (c) 1997-2001 by Secret Labs AB
"""

import array, operator, sys
from sre_constants import ATCODES, OPCODES, CHCODES, MAXREPEAT
from sre_constants import SRE_INFO_PREFIX, SRE_INFO_LITERAL
from sre_constants import SRE_FLAG_UNICODE, SRE_FLAG_LOCALE
import _sre
from _sre import CODESIZE


def compile(pattern, flags, code, groups=0, groupindex={}, indexgroup=[None]):
    """Compiles (or rather just converts) a pattern descriptor to a SRE_Pattern
    object. Actual compilation to opcodes happens in sre_compile."""
    return SRE_Pattern(pattern, flags, code, groups, groupindex, indexgroup)


class SRE_Pattern(object):

    def __init__(self, pattern, flags, code, groups=0, groupindex={}, indexgroup=[None]):
        self.pattern = pattern
        self.flags = flags
        self.groups = groups
        self.groupindex = groupindex # Maps group names to group indices
        self._indexgroup = indexgroup # Maps indices to group names
        self._code = code
    
    def match(self, string, pos=0, endpos=sys.maxint):
        """If zero or more characters at the beginning of string match this
        regular expression, return a corresponding MatchObject instance. Return
        None if the string does not match the pattern."""
        state = _sre._State(string, pos, endpos, self.flags)
        if _sre._match(state, self._code):
            return SRE_Match(self, state)
        else:
            return None

    def search(self, string, pos=0, endpos=sys.maxint):
        """Scan through string looking for a location where this regular
        expression produces a match, and return a corresponding MatchObject
        instance. Return None if no position in the string matches the
        pattern."""
        state = _sre._State(string, pos, endpos, self.flags)
        if search(state, self._code):
            return SRE_Match(self, state)
        else:
            return None

    def findall(self, string, pos=0, endpos=sys.maxint):
        """Return a list of all non-overlapping matches of pattern in string."""
        matchlist = []
        state = _sre._State(string, pos, endpos, self.flags)
        while state.start <= state.end:
            state.reset()
            state.string_position = state.start
            if not search(state, self._code):
                break
            match = SRE_Match(self, state)
            if self.groups == 0 or self.groups == 1:
                item = match.group(self.groups)
            else:
                item = match.groups("")
            matchlist.append(item)
            if state.string_position == state.start:
                state.start += 1
            else:
                state.start = state.string_position
        return matchlist        
        
    def _subx(self, template, string, count=0, subn=False):
        filter = template
        if not callable(template) and "\\" in template:
            # handle non-literal strings ; hand it over to the template compiler
            import sre
            filter = sre._subx(self, template)
        state = _sre._State(string, 0, sys.maxint, self.flags)
        sublist = []
        
        n = last_pos = 0
        while not count or n < count:
            state.reset()
            state.string_position = state.start
            if not search(state, self._code):
                break
            if last_pos < state.start:
                sublist.append(string[last_pos:state.start])
            if not (last_pos == state.start and
                                last_pos == state.string_position and n > 0):
                # the above ignores empty matches on latest position
                if callable(filter):
                    sublist.append(filter(SRE_Match(self, state)))
                else:
                    sublist.append(filter)
                last_pos = state.string_position
                n += 1
            if state.string_position == state.start:
                state.start += 1
            else:
                state.start = state.string_position

        if last_pos < state.end:
            sublist.append(string[last_pos:state.end])
        item = "".join(sublist)
        if subn:
            return item, n
        else:
            return item

    def sub(self, repl, string, count=0):
        """Return the string obtained by replacing the leftmost non-overlapping
        occurrences of pattern in string by the replacement repl."""
        return self._subx(repl, string, count, False)

    def subn(self, repl, string, count=0):
        """Return the tuple (new_string, number_of_subs_made) found by replacing
        the leftmost non-overlapping occurrences of pattern with the replacement
        repl."""
        return self._subx(repl, string, count, True)
        
    def split(self, string, maxsplit=0):
        """Split string by the occurrences of pattern."""
        splitlist = []
        state = _sre._State(string, 0, sys.maxint, self.flags)
        n = 0
        last = state.start
        while not maxsplit or n < maxsplit:
            state.reset()
            state.string_position = state.start
            if not search(state, self._code):
                break
            if state.start == state.string_position: # zero-width match
                if last == state.end:                # or end of string
                    break
                state.start += 1
                continue
            splitlist.append(string[last:state.start])
            # add groups (if any)
            if self.groups:
                match = SRE_Match(self, state)
                splitlist.extend(list(match.groups(None)))
            n += 1
            last = state.start = state.string_position
        splitlist.append(string[last:state.end])
        return splitlist

    def finditer(self, string, pos=0, endpos=sys.maxint):
        """Return a list of all non-overlapping matches of pattern in string."""
        scanner = self.scanner(string, pos, endpos)
        return iter(scanner.search, None)

    def scanner(self, string, start=0, end=sys.maxint):
        return SRE_Scanner(self, string, start, end)
    
    def __copy__(self):
        raise TypeError, "cannot copy this pattern object"

    def __deepcopy__(self):
        raise TypeError, "cannot copy this pattern object"


class SRE_Scanner(object):
    """Undocumented scanner interface of sre."""
    
    def __init__(self, pattern, string, start, end):
        self.pattern = pattern
        self._state = _sre._State(string, start, end, self.pattern.flags)

    def _match_search(self, matcher):
        state = self._state
        state.reset()
        state.string_position = state.start
        match = None
        if matcher(state, self.pattern._code):
            match = SRE_Match(self.pattern, state)
        if match is None or state.string_position == state.start:
            state.start += 1
        else:
            state.start = state.string_position
        return match

    def match(self):
        return self._match_search(_sre._match)

    def search(self):
        return self._match_search(search)


class SRE_Match(object):

    def __init__(self, pattern, state):
        self.re = pattern
        self.string = state.string
        self.pos = state.pos
        self.endpos = state.end
        self.lastindex = state.lastindex
        if self.lastindex < 0:
            self.lastindex = None
        self.regs = state.create_regs(self.re.groups)
        if pattern._indexgroup and 0 <= self.lastindex < len(pattern._indexgroup):
            # The above upper-bound check should not be necessary, as the re
            # compiler is supposed to always provide an _indexgroup list long
            # enough. But the re.Scanner class seems to screw up something
            # there, test_scanner in test_re won't work without upper-bound
            # checking. XXX investigate this and report bug to CPython.
            self.lastgroup = pattern._indexgroup[self.lastindex]
        else:
            self.lastgroup = None

    def _get_index(self, group):
        if isinstance(group, int):
            if group >= 0 and group <= self.re.groups:
                return group
        else:
            if self.re.groupindex.has_key(group):
                return self.re.groupindex[group]
        raise IndexError("no such group")

    def _get_slice(self, group, default):
        group_indices = self.regs[group]
        if group_indices[0] >= 0:
            return self.string[group_indices[0]:group_indices[1]]
        else:
            return default

    def start(self, group=0):
        """Returns the indices of the start of the substring matched by group;
        group defaults to zero (meaning the whole matched substring). Returns -1
        if group exists but did not contribute to the match."""
        return self.regs[self._get_index(group)][0]

    def end(self, group=0):
        """Returns the indices of the end of the substring matched by group;
        group defaults to zero (meaning the whole matched substring). Returns -1
        if group exists but did not contribute to the match."""
        return self.regs[self._get_index(group)][1]

    def span(self, group=0):
        """Returns the 2-tuple (m.start(group), m.end(group))."""
        return self.start(group), self.end(group)
        
    def expand(self, template):
        """Return the string obtained by doing backslash substitution and
        resolving group references on template."""
        import sre
        return sre._expand(self.re, self, template)
        
    def groups(self, default=None):
        """Returns a tuple containing all the subgroups of the match. The
        default argument is used for groups that did not participate in the
        match (defaults to None)."""
        groups = []
        for indices in self.regs[1:]:
            if indices[0] >= 0:
                groups.append(self.string[indices[0]:indices[1]])
            else:
                groups.append(default)
        return tuple(groups)
        
    def groupdict(self, default=None):
        """Return a dictionary containing all the named subgroups of the match.
        The default argument is used for groups that did not participate in the
        match (defaults to None)."""
        groupdict = {}
        for key, value in self.re.groupindex.items():
            groupdict[key] = self._get_slice(value, default)
        return groupdict

    def group(self, *args):
        """Returns one or more subgroups of the match. Each argument is either a
        group index or a group name."""
        if len(args) == 0:
            args = (0,)
        grouplist = []
        for group in args:
            grouplist.append(self._get_slice(self._get_index(group), None))
        if len(grouplist) == 1:
            return grouplist[0]
        else:
            return tuple(grouplist)

    def __copy__():
        raise TypeError, "cannot copy this pattern object"

    def __deepcopy__():
        raise TypeError, "cannot copy this pattern object"


def search(state, pattern_codes):
    flags = 0
    if pattern_codes[0] == OPCODES["info"]:
        # optimization info block
        # <INFO> <1=skip> <2=flags> <3=min> <4=max> <5=prefix info>
        #if pattern_codes[2] & SRE_INFO_PREFIX and pattern_codes[5] > 1:
        #    return state.fast_search(pattern_codes)
        flags = pattern_codes[2]
        pattern_codes = pattern_codes[pattern_codes[1] + 1:]

    string_position = state.start
    """
    if pattern_codes[0] == OPCODES["literal"]:
        # Special case: Pattern starts with a literal character. This is
        # used for short prefixes
        character = pattern_codes[1]
        while True:
            while string_position < state.end \
                    and ord(state.string[string_position]) != character:
                string_position += 1
            if string_position >= state.end:
                return False
            state.start = string_position
            string_position += 1
            state.string_position = string_position
            if flags & SRE_INFO_LITERAL:
                return True
            if match(state, pattern_codes[2:]):
                return True
        return False
    """

    # General case
    while string_position <= state.end:
        state.reset()
        state.start = state.string_position = string_position
        if _sre._match(state, pattern_codes):
            return True
        string_position += 1
    return False


def fast_search(state, pattern_codes):
    """Skips forward in a string as fast as possible using information from
    an optimization info block."""
    # pattern starts with a known prefix
    # <5=length> <6=skip> <7=prefix data> <overlap data>
    flags = pattern_codes[2]
    prefix_len = pattern_codes[5]
    prefix_skip = pattern_codes[6] # don't really know what this is good for
    prefix = pattern_codes[7:7 + prefix_len]
    overlap = pattern_codes[7 + prefix_len - 1:pattern_codes[1] + 1]
    pattern_codes = pattern_codes[pattern_codes[1] + 1:]
    i = 0
    string_position = state.string_position
    while string_position < state.end:
        while True:
            if ord(state.string[string_position]) != prefix[i]:
                if i == 0:
                    break
                else:
                    i = overlap[i]
            else:
                i += 1
                if i == prefix_len:
                    # found a potential match
                    state.start = string_position + 1 - prefix_len
                    state.string_position = string_position + 1 \
                                                 - prefix_len + prefix_skip
                    if flags & SRE_INFO_LITERAL:
                        return True # matched all of pure literal pattern
                    if _sre._match(state, pattern_codes[2 * prefix_skip:]):
                        return True
                    i = overlap[i]
                break
        string_position += 1
    return False

# XXX temporary constants for MatchContext.has_matched
UNDECIDED = 0
MATCHED = 1
NOT_MATCHED = 2

def match(state, pattern_codes):
    # Optimization: Check string length. pattern_codes[3] contains the
    # minimum length for a string to possibly match.
    if pattern_codes[0] == OPCODES["info"] and pattern_codes[3]:
        if state.end - state.string_position < pattern_codes[3]:
            #_log("reject (got %d chars, need %d)"
            #         % (state.end - state.string_position, pattern_codes[3]))
            return False
    
    dispatcher = _OpcodeDispatcher()
    state.context_stack.append(_sre._MatchContext(state, pattern_codes))
    has_matched = UNDECIDED
    while len(state.context_stack) > 0:
        context = state.context_stack[-1]
        has_matched = dispatcher.match(context)
        if has_matched != UNDECIDED: # don't pop if context isn't done
            state.context_stack.pop()
    return has_matched == MATCHED


def _log(message):
    if 0:
        print message
