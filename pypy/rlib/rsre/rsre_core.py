import sys
from pypy.rlib.debug import check_nonneg
from pypy.rlib.rsre import rsre_char
from pypy.rlib import jit


OPCODE_FAILURE            = 0
OPCODE_SUCCESS            = 1
OPCODE_ANY                = 2
OPCODE_ANY_ALL            = 3
OPCODE_ASSERT             = 4
OPCODE_ASSERT_NOT         = 5
OPCODE_AT                 = 6
OPCODE_BRANCH             = 7
#OPCODE_CALL              = 8
#OPCODE_CATEGORY          = 9
#OPCODE_CHARSET           = 10
#OPCODE_BIGCHARSET        = 11
OPCODE_GROUPREF           = 12
OPCODE_GROUPREF_EXISTS    = 13
OPCODE_GROUPREF_IGNORE    = 14
OPCODE_IN                 = 15
OPCODE_IN_IGNORE          = 16
OPCODE_INFO               = 17
OPCODE_JUMP               = 18
OPCODE_LITERAL            = 19
OPCODE_LITERAL_IGNORE     = 20
OPCODE_MARK               = 21
OPCODE_MAX_UNTIL          = 22
OPCODE_MIN_UNTIL          = 23
OPCODE_NOT_LITERAL        = 24
OPCODE_NOT_LITERAL_IGNORE = 25
#OPCODE_NEGATE            = 26
#OPCODE_RANGE             = 27
OPCODE_REPEAT             = 28
OPCODE_REPEAT_ONE         = 29
#OPCODE_SUBPATTERN        = 30
OPCODE_MIN_REPEAT_ONE     = 31


class MatchContext(object):
    match_start = 0
    match_end = 0
    match_marks = None
    match_marks_flat = None

    def __init__(self, pattern, string, match_start, end, flags):
        self.pattern = pattern
        self.string = string
        if end > len(string):
            end = len(string)
        self.end = end
        self.match_start = match_start
        self.flags = flags

    def pat(self, index):
        check_nonneg(index)
        return self.pattern[index]

    def str(self, index):
        check_nonneg(index)
        return ord(self.string[index])

    def lowstr(self, index):
        c = self.str(index)
        return rsre_char.getlower(c, self.flags)

    def get_mark(self, gid):
        return find_mark(self.match_marks, gid)

    def flatten_marks(self):
        # for testing
        if self.match_marks_flat is None:
            self.match_marks_flat = [self.match_start, self.match_end]
            mark = self.match_marks
            if mark is not None:
                self.match_lastindex = mark.gid
            else:
                self.match_lastindex = -1
            while mark is not None:
                index = mark.gid + 2
                while index >= len(self.match_marks_flat):
                    self.match_marks_flat.append(-1)
                if self.match_marks_flat[index] == -1:
                    self.match_marks_flat[index] = mark.position
                mark = mark.prev
            self.match_marks = None    # clear
        return self.match_marks_flat

    def span(self, groupnum=0):
        # compatibility
        fmarks = self.flatten_marks()
        groupnum *= 2
        if groupnum >= len(fmarks):
            return (-1, -1)
        return (fmarks[groupnum], fmarks[groupnum+1])

    def group(self, groupnum=0):
        # compatibility
        frm, to = self.span(groupnum)
        if 0 <= frm <= to:
            return self.string[frm:to]
        else:
            return None

    def at_boundary(self, ptr, word_checker):
        if self.end == 0:
            return False
        prevptr = ptr - 1
        that = prevptr >= 0 and word_checker(self.str(prevptr))
        this = ptr < self.end and word_checker(self.str(ptr))
        return this != that
    at_boundary._annspecialcase_ = 'specialize:arg(2)'

    def at_non_boundary(self, ptr, word_checker):
        if self.end == 0:
            return False
        prevptr = ptr - 1
        that = prevptr >= 0 and word_checker(self.str(prevptr))
        this = ptr < self.end and word_checker(self.str(ptr))
        return this == that
    at_non_boundary._annspecialcase_ = 'specialize:arg(2)'


class Mark(object):
    _immutable_ = True

    def __init__(self, gid, position, prev):
        self.gid = gid
        self.position = position
        self.prev = prev      # chained list

def find_mark(mark, gid):
    while mark is not None:
        if mark.gid == gid:
            return mark.position
        mark = mark.prev
    return -1


class MatchResult(object):
    subresult = None

    def move_to_next_result(self, ctx):
        result = self.subresult
        if result is None:
            return
        if result.move_to_next_result(ctx):
            return result
        return self.find_next_result(ctx)

    def find_next_result(self, ctx):
        raise NotImplementedError

MATCHED_OK = MatchResult()

class BranchMatchResult(MatchResult):

    def __init__(self, ppos, ptr, marks):
        self.ppos = ppos
        self.start_ptr = ptr
        self.start_marks = marks

    @jit.unroll_safe     # there are only a few branch alternatives
    def find_first_result(self, ctx):
        ppos = self.ppos
        while ctx.pat(ppos):
            result = sre_match(ctx, ppos + 1, self.start_ptr, self.start_marks)
            ppos += ctx.pat(ppos)
            if result is not None:
                self.subresult = result
                self.ppos = ppos
                return self
    find_next_result = find_first_result

class RepeatOneMatchResult(MatchResult):

    def __init__(self, nextppos, minptr, ptr, marks):
        self.nextppos = nextppos
        self.minptr = minptr
        self.start_ptr = ptr
        self.start_marks = marks

    def find_first_result(self, ctx):
        ptr = self.start_ptr
        while ptr >= self.minptr:
            result = sre_match(ctx, self.nextppos, ptr, self.start_marks)
            ptr -= 1
            if result is not None:
                self.subresult = result
                self.start_ptr = ptr
                return self
    find_next_result = find_first_result


class MinRepeatOneMatchResult(MatchResult):

    def __init__(self, nextppos, ppos3, maxptr, ptr, marks):
        self.nextppos = nextppos
        self.ppos3 = ppos3
        self.maxptr = maxptr
        self.start_ptr = ptr
        self.start_marks = marks

    def find_first_result(self, ctx):
        ptr = self.start_ptr
        while ptr <= self.maxptr:
            result = sre_match(ctx, self.nextppos, ptr, self.start_marks)
            if result is not None:
                self.subresult = result
                self.start_ptr = ptr
                return self
            ptr1 = find_repetition_end(ctx, self.ppos3, ptr, 1)
            if ptr1 == ptr:
                break
            ptr = ptr1

    def find_next_result(self, ctx):
        ptr = self.start_ptr
        ptr1 = find_repetition_end(ctx, self.ppos3, ptr, 1)
        if ptr1 == ptr:
            return
        self.start_ptr = ptr1
        return self.find_first_result(ctx)

class AbstractUntilMatchResult(MatchResult):

    def __init__(self, ppos, tailppos, ptr, marks):
        self.ppos = ppos
        self.tailppos = tailppos
        self.cur_ptr = ptr
        self.cur_marks = marks
        self.pending = None
        self.num_pending = 0

class Pending(object):
    def __init__(self, ptr, marks, enum, next):
        self.ptr = ptr
        self.marks = marks
        self.enum = enum
        self.next = next     # chained list

class MaxUntilMatchResult(AbstractUntilMatchResult):

    def find_first_result(self, ctx):
        enum = sre_match(ctx, self.ppos + 3, self.cur_ptr, self.cur_marks)
        return self.search_next(ctx, enum, resume=False)

    def find_next_result(self, ctx):
        return self.search_next(ctx, None, resume=True)

    def search_next(self, ctx, enum, resume):
        ppos = self.ppos
        min = ctx.pat(ppos+1)
        max = ctx.pat(ppos+2)
        ptr = self.cur_ptr
        marks = self.cur_marks
        while True:
            while True:
                if enum is not None:
                    # matched one more 'item'.  record it and continue
                    self.pending = Pending(ptr, marks, enum, self.pending)
                    self.num_pending += 1
                    ptr = ctx.match_end
                    marks = ctx.match_marks
                    break
                else:
                    # 'item' no longer matches.
                    if not resume and self.num_pending >= min:
                        # try to match 'tail' if we have enough 'item'
                        result = sre_match(ctx, self.tailppos, ptr, marks)
                        if result is not None:
                            self.subresult = result
                            self.cur_ptr = ptr
                            self.cur_marks = marks
                            return self
                    resume = False
                    p = self.pending
                    if p is None:
                        return
                    self.pending = p.next
                    self.num_pending -= 1
                    ptr = p.ptr
                    marks = p.marks
                    enum = p.enum.move_to_next_result(ctx)
            #
            if max == 65535 or self.num_pending < max:
                # try to match one more 'item'
                enum = sre_match(ctx, ppos + 3, ptr, marks)
            else:
                enum = None    # 'max' reached, no more matches

class MinUntilMatchResult(AbstractUntilMatchResult):

    def find_first_result(self, ctx):
        return self.search_next(ctx, resume=False)

    def find_next_result(self, ctx):
        return self.search_next(ctx, resume=True)

    def search_next(self, ctx, resume):
        ppos = self.ppos
        min = ctx.pat(ppos+1)
        max = ctx.pat(ppos+2)
        ptr = self.cur_ptr
        marks = self.cur_marks
        while True:
            # try to match 'tail' if we have enough 'item'
            if not resume and self.num_pending >= min:
                result = sre_match(ctx, self.tailppos, ptr, marks)
                if result is not None:
                    self.subresult = result
                    self.cur_ptr = ptr
                    self.cur_marks = marks
                    return self
            resume = False

            if max == 65535 or self.num_pending < max:
                # try to match one more 'item'
                enum = sre_match(ctx, ppos + 3, ptr, marks)
            else:
                enum = None    # 'max' reached, no more matches

            while enum is None:
                # 'item' does not match; try to get further results from
                # the 'pending' list.
                p = self.pending
                if p is None:
                    return
                self.pending = p.next
                self.num_pending -= 1
                ptr = p.ptr
                marks = p.marks
                enum = p.enum.move_to_next_result(ctx)

            # matched one more 'item'.  record it and continue
            self.pending = Pending(ptr, marks, enum, self.pending)
            self.num_pending += 1
            ptr = ctx.match_end
            marks = ctx.match_marks

# ____________________________________________________________

@jit.unroll_safe      # it's safe to unroll the main 'while' loop:
                      # 'ppos' is only ever incremented in this function
def sre_match(ctx, ppos, ptr, marks):
    """Returns either None or a MatchResult object.  Usually we only need
    the first result, but there is the case of REPEAT...UNTIL where we
    need all results; in that case we use the method move_to_next_result()
    of the MatchResult."""
    while True:
        op = ctx.pat(ppos)
        ppos += 1

        if op == OPCODE_FAILURE:
            return

        if (op == OPCODE_SUCCESS or
            op == OPCODE_MAX_UNTIL or
            op == OPCODE_MIN_UNTIL):
            ctx.match_end = ptr
            ctx.match_marks = marks
            return MATCHED_OK

        elif op == OPCODE_ANY:
            # match anything (except a newline)
            # <ANY>
            if ptr >= ctx.end or rsre_char.is_linebreak(ctx.str(ptr)):
                return
            ptr += 1

        elif op == OPCODE_ANY_ALL:
            # match anything
            # <ANY_ALL>
            if ptr >= ctx.end:
                return
            ptr += 1

        elif op == OPCODE_ASSERT:
            # assert subpattern
            # <ASSERT> <0=skip> <1=back> <pattern>
            ptr1 = ptr - ctx.pat(ppos+1)
            if ptr1 < 0 or sre_match(ctx, ppos + 2, ptr1, marks) is None:
                return
            marks = ctx.match_marks
            ppos += ctx.pat(ppos)

        elif op == OPCODE_ASSERT_NOT:
            # assert not subpattern
            # <ASSERT_NOT> <0=skip> <1=back> <pattern>
            ptr1 = ptr - ctx.pat(ppos+1)
            if ptr1 >= 0 and sre_match(ctx, ppos + 2, ptr1, marks) is not None:
                return
            ppos += ctx.pat(ppos)

        elif op == OPCODE_AT:
            # match at given position (e.g. at beginning, at boundary, etc.)
            # <AT> <code>
            if not sre_at(ctx, ctx.pat(ppos), ptr):
                return
            ppos += 1

        elif op == OPCODE_BRANCH:
            # alternation
            # <BRANCH> <0=skip> code <JUMP> ... <NULL>
            result = BranchMatchResult(ppos, ptr, marks)
            return result.find_first_result(ctx)

        #elif op == OPCODE_CATEGORY:
        #   seems to be never produced

        elif op == OPCODE_GROUPREF:
            # match backreference
            # <GROUPREF> <groupnum>
            startptr, length = get_group_ref(marks, ctx.pat(ppos))
            if length < 0:
                return     # group was not previously defined
            if not match_repeated(ctx, ptr, startptr, length):
                return     # no match
            ptr += length
            ppos += 1

        elif op == OPCODE_GROUPREF_IGNORE:
            # match backreference
            # <GROUPREF> <groupnum>
            startptr, length = get_group_ref(marks, ctx.pat(ppos))
            if length < 0:
                return     # group was not previously defined
            if not match_repeated_ignore(ctx, ptr, startptr, length):
                return     # no match
            ptr += length
            ppos += 1

        elif op == OPCODE_GROUPREF_EXISTS:
            # conditional match depending on the existence of a group
            # <GROUPREF_EXISTS> <group> <skip> codeyes <JUMP> codeno ...
            _, length = get_group_ref(marks, ctx.pat(ppos))
            if length >= 0:
                ppos += 2                  # jump to 'codeyes'
            else:
                ppos += ctx.pat(ppos+1)    # jump to 'codeno'

        elif op == OPCODE_IN:
            # match set member (or non_member)
            # <IN> <skip> <set>
            if ptr >= ctx.end or not rsre_char.check_charset(ctx.pattern,
                                                             ppos+1,
                                                             ctx.str(ptr)):
                return
            ppos += ctx.pat(ppos)
            ptr += 1

        elif op == OPCODE_IN_IGNORE:
            # match set member (or non_member), ignoring case
            # <IN> <skip> <set>
            if ptr >= ctx.end or not rsre_char.check_charset(ctx.pattern,
                                                             ppos+1,
                                                             ctx.lowstr(ptr)):
                return
            ppos += ctx.pat(ppos)
            ptr += 1

        elif op == OPCODE_INFO:
            # optimization info block
            # <INFO> <0=skip> <1=flags> <2=min> ...
            if (ctx.end - ptr) < ctx.pat(ppos+2):
                return
            ppos += ctx.pat(ppos)

        elif op == OPCODE_JUMP:
            ppos += ctx.pat(ppos)

        elif op == OPCODE_LITERAL:
            # match literal string
            # <LITERAL> <code>
            if ptr >= ctx.end or ctx.str(ptr) != ctx.pat(ppos):
                return
            ppos += 1
            ptr += 1

        elif op == OPCODE_LITERAL_IGNORE:
            # match literal string, ignoring case
            # <LITERAL_IGNORE> <code>
            if ptr >= ctx.end or ctx.lowstr(ptr) != ctx.pat(ppos):
                return
            ppos += 1
            ptr += 1

        elif op == OPCODE_MARK:
            # set mark
            # <MARK> <gid>
            gid = ctx.pat(ppos)
            marks = Mark(gid, ptr, marks)
            ppos += 1

        elif op == OPCODE_NOT_LITERAL:
            # match if it's not a literal string
            # <NOT_LITERAL> <code>
            if ptr >= ctx.end or ctx.str(ptr) == ctx.pat(ppos):
                return
            ppos += 1
            ptr += 1

        elif op == OPCODE_NOT_LITERAL_IGNORE:
            # match if it's not a literal string, ignoring case
            # <NOT_LITERAL> <code>
            if ptr >= ctx.end or ctx.lowstr(ptr) == ctx.pat(ppos):
                return
            ppos += 1
            ptr += 1

        elif op == OPCODE_REPEAT:
            # general repeat.  in this version of the re module, all the work
            # is done here, and not on the later UNTIL operator.
            # <REPEAT> <skip> <1=min> <2=max> item <UNTIL> tail
            # FIXME: we probably need to deal with zero-width matches in here..

            # decode the later UNTIL operator to see if it is actually
            # a MAX_UNTIL or MIN_UNTIL
            untilppos = ppos + ctx.pat(ppos)
            tailppos = untilppos + 1
            op = ctx.pat(untilppos)
            if op == OPCODE_MAX_UNTIL:
                # the hard case: we have to match as many repetitions as
                # possible, followed by the 'tail'.  we do this by
                # remembering each state for each possible number of
                # 'item' matching.
                result = MaxUntilMatchResult(ppos, tailppos, ptr, marks)
                return result.find_first_result(ctx)

            elif op == OPCODE_MIN_UNTIL:
                # first try to match the 'tail', and if it fails, try
                # to match one more 'item' and try again
                result = MinUntilMatchResult(ppos, tailppos, ptr, marks)
                return result.find_first_result(ctx)

            else:
                raise AssertionError("missing UNTIL after REPEAT")

        elif op == OPCODE_REPEAT_ONE:
            # match repeated sequence (maximizing regexp).
            # this operator only works if the repeated item is
            # exactly one character wide, and we're not already
            # collecting backtracking points.  for other cases,
            # use the MAX_REPEAT operator.
            # <REPEAT_ONE> <skip> <1=min> <2=max> item <SUCCESS> tail
            start = ptr
            minptr = start + ctx.pat(ppos+1)
            if minptr > ctx.end:
                return    # cannot match
            ptr = find_repetition_end(ctx, ppos+3, start, ctx.pat(ppos+2))
            # when we arrive here, ptr points to the tail of the target
            # string.  check if the rest of the pattern matches,
            # and backtrack if not.
            nextppos = ppos + ctx.pat(ppos)
            result = RepeatOneMatchResult(nextppos, minptr, ptr, marks)
            return result.find_first_result(ctx)

        elif op == OPCODE_MIN_REPEAT_ONE:
            # match repeated sequence (minimizing regexp).
            # this operator only works if the repeated item is
            # exactly one character wide, and we're not already
            # collecting backtracking points.  for other cases,
            # use the MIN_REPEAT operator.
            # <MIN_REPEAT_ONE> <skip> <1=min> <2=max> item <SUCCESS> tail
            start = ptr
            min = ctx.pat(ppos+1)
            if min > 0:
                minptr = ptr + min
                if minptr > ctx.end:
                    return   # cannot match
                # count using pattern min as the maximum
                ptr = find_repetition_end(ctx, ppos+3, ptr, min)
                if ptr < minptr:
                    return   # did not match minimum number of times

            maxptr = ctx.end
            max = ctx.pat(ppos+2)
            if max != 65535:
                maxptr1 = start + max
                if maxptr1 <= maxptr:
                    maxptr = maxptr1
            nextppos = ppos + ctx.pat(ppos)
            result = MinRepeatOneMatchResult(nextppos, ppos+3, maxptr,
                                             ptr, marks)
            return result.find_first_result(ctx)

        else:
            assert 0, "bad pattern code %d" % op


def get_group_ref(marks, groupnum):
    gid = groupnum * 2
    startptr = find_mark(marks, gid)
    if startptr < 0:
        return 0, -1
    endptr = find_mark(marks, gid + 1)
    length = endptr - startptr     # < 0 if endptr < startptr (or if endptr=-1)
    return startptr, length

def match_repeated(ctx, ptr, oldptr, length):
    if ptr + length > ctx.end:
        return False
    for i in range(length):
        if ctx.str(ptr + i) != ctx.str(oldptr + i):
            return False
    return True

def match_repeated_ignore(ctx, ptr, oldptr, length):
    if ptr + length > ctx.end:
        return False
    for i in range(length):
        if ctx.lowstr(ptr + i) != ctx.lowstr(oldptr + i):
            return False
    return True

def find_repetition_end(ctx, ppos, ptr, maxcount):
    end = ctx.end
    # adjust end
    if maxcount != 65535:
        end1 = ptr + maxcount
        if end1 <= end:
            end = end1

    op = ctx.pat(ppos)
    if op == OPCODE_ANY:            return fre_ANY(ctx, ptr, end)
    if op == OPCODE_ANY_ALL:        return end
    if op == OPCODE_IN:             return fre_IN(ctx, ptr, end, ppos)
    if op == OPCODE_IN_IGNORE:      return fre_IN_IGNORE(ctx, ptr, end, ppos)
    if op == OPCODE_LITERAL:        return fre_LITERAL(ctx, ptr, end, ppos)
    if op == OPCODE_LITERAL_IGNORE: return fre_LITERAL_IGNORE(ctx,ptr,end,ppos)
    if op == OPCODE_NOT_LITERAL:    return fre_NOT_LITERAL(ctx, ptr, end, ppos)
    if op == OPCODE_NOT_LITERAL_IGNORE: return fre_NOT_LITERAL_IGNORE(ctx,ptr,
                                                                      end,ppos)
    raise NotImplementedError("rsre.find_repetition_end[%d]" % op)

def fre_ANY(ctx, ptr, end):
    # repeated dot wildcard.
    while ptr < end and not rsre_char.is_linebreak(ctx.str(ptr)):
        ptr += 1
    return ptr

def fre_IN(ctx, ptr, end, ppos):
    # repeated set
    while ptr < end and rsre_char.check_charset(ctx.pattern, ppos+2,
                                                ctx.str(ptr)):
        ptr += 1
    return ptr

def fre_IN_IGNORE(ctx, ptr, end, ppos):
    # repeated set
    while ptr < end and rsre_char.check_charset(ctx.pattern, ppos+2,
                                                ctx.lowstr(ptr)):
        ptr += 1
    return ptr

def fre_LITERAL(ctx, ptr, end, ppos):
    chr = ctx.pat(ppos+1)
    while ptr < end and ctx.str(ptr) == chr:
        ptr += 1
    return ptr

def fre_LITERAL_IGNORE(ctx, ptr, end, ppos):
    chr = ctx.pat(ppos+1)
    while ptr < end and ctx.lowstr(ptr) == chr:
        ptr += 1
    return ptr

def fre_NOT_LITERAL(ctx, ptr, end, ppos):
    chr = ctx.pat(ppos+1)
    while ptr < end and ctx.str(ptr) != chr:
        ptr += 1
    return ptr

def fre_NOT_LITERAL_IGNORE(ctx, ptr, end, ppos):
    chr = ctx.pat(ppos+1)
    while ptr < end and ctx.lowstr(ptr) != chr:
        ptr += 1
    return ptr

##### At dispatch

AT_BEGINNING = 0
AT_BEGINNING_LINE = 1
AT_BEGINNING_STRING = 2
AT_BOUNDARY = 3
AT_NON_BOUNDARY = 4
AT_END = 5
AT_END_LINE = 6
AT_END_STRING = 7
AT_LOC_BOUNDARY = 8
AT_LOC_NON_BOUNDARY = 9
AT_UNI_BOUNDARY = 10
AT_UNI_NON_BOUNDARY = 11

def sre_at(ctx, atcode, ptr):
    if (atcode == AT_BEGINNING or
        atcode == AT_BEGINNING_STRING):
        return ptr == 0

    elif atcode == AT_BEGINNING_LINE:
        prevptr = ptr - 1
        return prevptr < 0 or rsre_char.is_linebreak(ctx.str(prevptr))

    elif atcode == AT_BOUNDARY:
        return ctx.at_boundary(ptr, rsre_char.is_word)

    elif atcode == AT_NON_BOUNDARY:
        return ctx.at_non_boundary(ptr, rsre_char.is_word)

    elif atcode == AT_END:
        remaining_chars = ctx.end - ptr
        return remaining_chars <= 0 or (
            remaining_chars == 1 and rsre_char.is_linebreak(ctx.str(ptr)))

    elif atcode == AT_END_LINE:
        return ptr == ctx.end or rsre_char.is_linebreak(ctx.str(ptr))

    elif atcode == AT_END_STRING:
        return ptr == ctx.end

    elif atcode == AT_LOC_BOUNDARY:
        return ctx.at_boundary(ptr, rsre_char.is_loc_word)

    elif atcode == AT_LOC_NON_BOUNDARY:
        return ctx.at_non_boundary(ptr, rsre_char.is_loc_word)

    elif atcode == AT_UNI_BOUNDARY:
        return ctx.at_boundary(ptr, rsre_char.is_uni_word)

    elif atcode == AT_UNI_NON_BOUNDARY:
        return ctx.at_non_boundary(ptr, rsre_char.is_uni_word)

    return False

# ____________________________________________________________

def match(pattern, string, start=0, end=sys.maxint, flags=0):
    if start < 0: start = 0
    if end < start: return None
    ctx = MatchContext(pattern, string, start, end, flags)
    if sre_match(ctx, 0, start, None) is not None:
        return ctx
    return None

def search(pattern, string, start=0, end=sys.maxint, flags=0):
    if start < 0: start = 0
    if end < start: return None
    ctx = MatchContext(pattern, string, start, end, flags)
    if ctx.pat(0) == OPCODE_INFO:
        if ctx.pat(2) & rsre_char.SRE_INFO_PREFIX and ctx.pat(5) > 1:
            return fast_search(ctx)
    return regular_search(ctx)

def regular_search(ctx):
    start = ctx.match_start
    while start <= ctx.end:
        if sre_match(ctx, 0, start, None) is not None:
            ctx.match_start = start
            return ctx
        start += 1
    return None

def fast_search(ctx):
    # skips forward in a string as fast as possible using information from
    # an optimization info block
    # <INFO> <1=skip> <2=flags> <3=min> <4=...>
    #        <5=length> <6=skip> <7=prefix data> <overlap data>
    flags = ctx.pat(2)
    prefix_len = ctx.pat(5)
    assert prefix_len >= 0
    prefix_skip = ctx.pat(6)
    assert prefix_skip >= 0
    overlap_offset = 7 + prefix_len - 1
    assert overlap_offset >= 0
    pattern_offset = ctx.pat(1) + 1
    assert pattern_offset >= 0
    i = 0
    string_position = ctx.match_start
    end = ctx.end
    while string_position < end:
        while True:
            char_ord = ctx.str(string_position)
            if char_ord != ctx.pat(7 + i):
                if i == 0:
                    break
                else:
                    i = ctx.pat(overlap_offset + i)
            else:
                i += 1
                if i == prefix_len:
                    # found a potential match
                    start = string_position + 1 - prefix_len
                    assert start >= 0
                    ptr = start + prefix_skip
                    if flags & rsre_char.SRE_INFO_LITERAL:
                        # matched all of pure literal pattern
                        ctx.match_start = start
                        ctx.match_end = ptr
                        ctx.match_marks = None
                        return ctx
                    ppos = pattern_offset + 2 * prefix_skip
                    if sre_match(ctx, ppos, ptr, None) is not None:
                        ctx.match_start = start
                        return ctx
                    i = ctx.pat(overlap_offset + i)
                break
        string_position += 1
    return None
