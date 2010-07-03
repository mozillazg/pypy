from pypy.rlib.debug import check_nonneg
from pypy.rlib.rsre import rsre_char


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

    def __init__(self, pattern, string, match_start, flags):
        self.pattern = pattern
        self.string = string
        self.end = len(string)
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
        lst = self.flatten_marks()[groupnum*2:groupnum*2+2]
        if not lst: raise IndexError
        return tuple(lst)

    def group(self, group=0):
        # compatibility
        frm, to = self.span(group)
        return self.string[frm:to]


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


def match(pattern, string, start=0, flags=0):
    ctx = MatchContext(pattern, string, start, flags)
    if sre_match(ctx, 0, start, None):
        return ctx
    return None

def sre_match(ctx, ppos, ptr, marks):
    while True:
        op = ctx.pat(ppos)
        ppos += 1

        if op == OPCODE_FAILURE:
            return False

        if (op == OPCODE_SUCCESS or
            op == OPCODE_MAX_UNTIL or
            op == OPCODE_MIN_UNTIL):
            ctx.match_end = ptr
            ctx.match_marks = marks
            return True

        elif op == OPCODE_ANY:
            # match anything (except a newline)
            # <ANY>
            if ptr >= ctx.end or rsre_char.is_linebreak(ctx.str(ptr)):
                return False
            ptr += 1

        elif op == OPCODE_ANY_ALL:
            # match anything
            # <ANY_ALL>
            if ptr >= ctx.end:
                return False
            ptr += 1

        elif op == OPCODE_ASSERT:
            # assert subpattern
            # <ASSERT> <0=skip> <1=back> <pattern>
            ptr1 = ptr - ctx.pat(ppos+1)
            if ptr1 < 0 or not sre_match(ctx, ppos + 2, ptr1, marks):
                return False
            ppos += ctx.pat(ppos)

        elif op == OPCODE_ASSERT_NOT:
            # assert not subpattern
            # <ASSERT_NOT> <0=skip> <1=back> <pattern>
            ptr1 = ptr - ctx.pat(ppos+1)
            if ptr1 >= 0 and sre_match(ctx, ppos + 2, ptr1, marks):
                return False
            ppos += ctx.pat(ppos)

        elif op == OPCODE_AT:
            # match at given position (e.g. at beginning, at boundary, etc.)
            # <AT> <code>
            if not sre_at(ctx, ctx.pat(ppos), ptr):
                return False
            ppos += 1

        elif op == OPCODE_BRANCH:
            # alternation
            # <BRANCH> <0=skip> code <JUMP> ... <NULL>
            while ctx.pat(ppos):
                if sre_match(ctx, ppos + 1, ptr, marks):
                    return True
                ppos += ctx.pat(ppos)
            return False

        #elif op == OPCODE_CATEGORY:
        #   seems to be never produced

        elif op == OPCODE_GROUPREF:
            # match backreference
            # <GROUPREF> <groupnum>
            gid = ctx.pat(ppos) * 2
            startptr = find_mark(marks, gid)
            if startptr < 0:
                return False
            endptr = find_mark(marks, gid + 1)
            if endptr < startptr:   # also includes the case "endptr == -1"
                return False
            for i in range(startptr, endptr):
                if ptr >= ctx.end or ctx.str(ptr) != ctx.str(i):
                    return False
                ptr += 1
            ppos += 1

        elif op == OPCODE_GROUPREF_IGNORE:
            # match backreference
            # <GROUPREF> <groupnum>
            gid = ctx.pat(ppos) * 2
            startptr = find_mark(marks, gid)
            if startptr < 0:
                return False
            endptr = find_mark(marks, gid + 1)
            if endptr < startptr:   # also includes the case "endptr == -1"
                return False
            for i in range(startptr, endptr):
                if ptr >= ctx.end or ctx.lowstr(ptr) != ctx.lowstr(i):
                    return False
                ptr += 1
            ppos += 1

        elif op == OPCODE_IN:
            # match set member (or non_member)
            # <IN> <skip> <set>
            if ptr >= ctx.end or not rsre_char.check_charset(ctx.pattern,
                                                             ppos+1,
                                                             ctx.str(ptr)):
                return False
            ppos += ctx.pat(ppos)
            ptr += 1

        elif op == OPCODE_IN_IGNORE:
            # match set member (or non_member), ignoring case
            # <IN> <skip> <set>
            if ptr >= ctx.end or not rsre_char.check_charset(ctx.pattern,
                                                             ppos+1,
                                                             ctx.lowstr(ptr)):
                return False
            ppos += ctx.pat(ppos)
            ptr += 1

        elif op == OPCODE_INFO:
            # optimization info block
            # <INFO> <0=skip> <1=flags> <2=min> ...
            if (ctx.end - ptr) < ctx.pat(ppos+2):
                return False
            ppos += ctx.pat(ppos)

        elif op == OPCODE_JUMP:
            ppos += ctx.pat(ppos)

        elif op == OPCODE_LITERAL:
            # match literal string
            # <LITERAL> <code>
            if ptr >= ctx.end or ctx.str(ptr) != ctx.pat(ppos):
                return False
            ppos += 1
            ptr += 1

        elif op == OPCODE_LITERAL_IGNORE:
            # match literal string, ignoring case
            # <LITERAL_IGNORE> <code>
            if ptr >= ctx.end or ctx.lowstr(ptr) != ctx.pat(ppos):
                return False
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
                return False
            ppos += 1
            ptr += 1

        elif op == OPCODE_NOT_LITERAL_IGNORE:
            # match if it's not a literal string, ignoring case
            # <NOT_LITERAL> <code>
            if ptr >= ctx.end or ctx.lowstr(ptr) == ctx.pat(ppos):
                return False
            ppos += 1
            ptr += 1

        elif op == OPCODE_REPEAT:
            # general repeat.  in this version of the re module, all the work
            # is done here, and not on the later UNTIL operator.
            # <REPEAT> <skip> <1=min> <2=max> item <UNTIL> tail
            itemppos = ppos + 3
            # FIXME: we probably need to deal with zero-width matches in here..

            # first match 'min' repetitions of 'item'
            min = ctx.pat(ppos+1)
            for i in range(min):
                if not sre_match(ctx, itemppos, ptr, marks):
                    return False
                ptr = ctx.match_end
                marks = ctx.match_marks

            # get the maximum number of repetitions allowed
            max = ctx.pat(ppos+2)

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
                pending_ptr = []
                pending_marks = []
                # match as many repetitions of 'item' as possible,
                # bounded by 'max'
                count = min
                while max == 65535 or count < max:
                    if not sre_match(ctx, itemppos, ptr, marks):
                        break
                    pending_ptr.append(ptr)
                    pending_marks.append(marks)
                    ptr = ctx.match_end
                    marks = ctx.match_marks
                    count += 1
                # for each pending_ptr in the chain, try to match 'tail';
                # return the first match found.  'ptr' is currently set
                # to where the last match of 'item' failed.
                while not sre_match(ctx, tailppos, ptr, marks):
                    if len(pending_ptr) == 0:
                        return False
                    ptr = pending_ptr.pop()
                    marks = pending_marks.pop()
                return True

            elif op == OPCODE_MIN_UNTIL:
                # first try to match the 'tail', and if it fails, try
                # to match one more 'item' and try again
                count = min
                while not sre_match(ctx, tailppos, ptr, marks):
                    if max != 65535 and count >= max:
                        return False
                    if not sre_match(ctx, itemppos, ptr, marks):
                        return False
                    ptr = ctx.match_end
                    marks = ctx.match_marks
                    count += 1
                return True

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
                return False    # cannot match
            ptr = find_repetition_end(ctx, ppos+3, start, ctx.pat(ppos+2))
            # when we arrive here, ptr points to the tail of the target
            # string.  check if the rest of the pattern matches,
            # and backtrack if not.
            nextppos = ppos + ctx.pat(ppos)
            while ptr >= minptr:
                if sre_match(ctx, nextppos, ptr, marks):
                    return True
                ptr -= 1
            return False

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
                    return False   # cannot match
                # count using pattern min as the maximum
                ptr = find_repetition_end(ctx, ppos+3, ptr, min)
                if ptr < minptr:
                    return False   # did not match minimum number of times

            maxptr = ctx.end
            max = ctx.pat(ppos+2)
            if max != 65535:
                maxptr1 = start + max
                if maxptr1 <= maxptr:
                    maxptr = maxptr1
            nextppos = ppos + ctx.pat(ppos)
            while ptr <= maxptr:
                if sre_match(ctx, nextppos, ptr, marks):
                    return True
                ptr1 = find_repetition_end(ctx, ppos+3, ptr, 1)
                if ptr1 == ptr:
                    break
                ptr = ptr1
            return False

        else:
            assert 0, "bad pattern code %d" % op


def find_repetition_end(ctx, ppos, ptr, maxcount):
    end = ctx.end
    # adjust end
    if maxcount != 65535:
        end1 = ptr + maxcount
        if end1 <= end:
            end = end1

    op = ctx.pat(ppos)

    if op == OPCODE_ANY:
        # repeated dot wildcard.
        while ptr < end and not rsre_char.is_linebreak(ctx.str(ptr)):
            ptr += 1

    elif op == OPCODE_ANY_ALL:
        # repeated dot wildcare.  skip to the end of the target
        # string, and backtrack from there
        ptr = end

    elif op == OPCODE_IN:
        # repeated set
        while ptr < end and rsre_char.check_charset(ctx.pattern, ppos+2,
                                                    ctx.str(ptr)):
            ptr += 1

    elif op == OPCODE_IN_IGNORE:
        # repeated set
        while ptr < end and rsre_char.check_charset(ctx.pattern, ppos+2,
                                                    ctx.lowstr(ptr)):
            ptr += 1

    elif op == OPCODE_LITERAL:
        chr = ctx.pat(ppos+1)
        while ptr < end and ctx.str(ptr) == chr:
            ptr += 1

    elif op == OPCODE_LITERAL_IGNORE:
        chr = ctx.pat(ppos+1)
        while ptr < end and ctx.lowstr(ptr) == chr:
            ptr += 1

    elif op == OPCODE_NOT_LITERAL:
        chr = ctx.pat(ppos+1)
        while ptr < end and ctx.str(ptr) != chr:
            ptr += 1

    elif op == OPCODE_NOT_LITERAL_IGNORE:
        chr = ctx.pat(ppos+1)
        while ptr < end and ctx.lowstr(ptr) != chr:
            ptr += 1

    else:
        assert 0, "XXX %d" % op

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
AT_UNI_BOUNDARY  =10
AT_UNI_NON_BOUNDARY  =11

def sre_at(ctx, atcode, ptr):
    if (atcode == AT_BEGINNING or
        atcode == AT_BEGINNING_STRING):
        return ptr == 0

    elif atcode == AT_BEGINNING_LINE:
        prevptr = ptr - 1
        return prevptr < 0 or rsre_char.is_linebreak(ctx.str(prevptr))

    elif atcode == AT_BOUNDARY:
        if ctx.end == 0:
            return False
        prevptr = ptr - 1
        that = prevptr >= 0 and is_word(ctx.str(prevptr))
        this = ptr < ctx.end and is_word(ctx.str(ptr))
        return this != that

    elif atcode == AT_NON_BOUNDARY:
        if ctx.end == 0:
            return False
        prevptr = ptr - 1
        that = prevptr >= 0 and is_word(ctx.str(prevptr))
        this = ptr < ctx.end and is_word(ctx.str(ptr))
        return this == that

    elif atcode == AT_END:
        remaining_chars = ctx.end - ptr
        return remaining_chars <= 0 or (
            remaining_chars == 1 and rsre_char.is_linebreak(ctx.str(ptr)))

    elif atcode == AT_END_LINE:
        return ptr == ctx.end or rsre_char.is_linebreak(ctx.str(ptr))

    elif atcode == AT_END_STRING:
        return ptr == ctx.end

    elif atcode == AT_LOC_BOUNDARY:
        XXX

    elif atcode == AT_LOC_NON_BOUNDARY:
        XXX

    elif atcode == AT_UNI_BOUNDARY:
        XXX

    elif atcode == AT_UNI_NON_BOUNDARY:
        XXX

    return False
