import sys
from rpython.rlib.rstring import StringBuilder
from rpython.rlib.objectmodel import specialize, always_inline
from rpython.rlib import rfloat, runicode, jit, objectmodel, rutf8
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import r_uint
from pypy.interpreter.error import oefmt
from pypy.interpreter import unicodehelper
from pypy.interpreter.baseobjspace import W_Root
from pypy.module._pypyjson import simd

OVF_DIGITS = len(str(sys.maxint))

def is_whitespace(ch):
    return ch == ' ' or ch == '\t' or ch == '\r' or ch == '\n'

# precomputing negative powers of 10 is MUCH faster than using e.g. math.pow
# at runtime
NEG_POW_10 = [10.0**-i for i in range(16)]
del i

def neg_pow_10(x, exp):
    if exp >= len(NEG_POW_10):
        return 0.0
    return x * NEG_POW_10[exp]

def _compare_cache_entry(space, res, ll_chars, start, length):
    if length != len(res):
        return False
    index = start
    for c in res:
        x = ord(c)
        if not ll_chars[index] == chr(x):
            return False
        index += 1
    return True


class IntCache(object):
    START = -10
    END = 256

    def __init__(self, space):
        self.space = space
        self.cache = [self.space.newint(i)
                for i in range(self.START, self.END)]

    def newint(self, intval):
        if self.START <= intval < self.END:
            return self.cache[intval - self.START]
        return self.space.newint(intval)


class JSONDecoder(W_Root):

    LRU_SIZE = 16
    LRU_MASK = LRU_SIZE - 1

    DEFAULT_SIZE_SCRATCH = 20

    MIN_SIZE_FOR_STRING_CACHE = 1024 * 1024


    def __init__(self, space, s):
        self.space = space
        self.w_empty_string = space.newutf8("", 0)

        self.s = s

        # we put our string in a raw buffer so:
        # 1) we automatically get the '\0' sentinel at the end of the string,
        #    which means that we never have to check for the "end of string"
        # 2) we can pass the buffer directly to strtod
        self.ll_chars, self.flag = rffi.get_nonmovingbuffer_final_null(self.s)
        self.end_ptr = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
        self.pos = 0
        self.intcache = space.fromcache(IntCache)

        self.cache = {}
        self.cache_wrapped = {}

        self.lru_cache = [0] * self.LRU_SIZE
        self.lru_index = 0

        self.startmap = self.space.fromcache(Terminator)
        self.unclear_objects = []

        self.scratch = [[None] * self.DEFAULT_SIZE_SCRATCH]  # list of scratch space


    def close(self):
        rffi.free_nonmovingbuffer(self.s, self.ll_chars, self.flag)
        lltype.free(self.end_ptr, flavor='raw')
        # clean up objects that are instances of now blocked maps
        for w_obj in self.unclear_objects:
            jsonmap = self._get_jsonmap_from_dict(w_obj)
            if jsonmap.is_blocked():
                self._devolve_jsonmap_dict(w_obj)

    def getslice(self, start, end):
        assert start >= 0
        assert end >= 0
        return self.s[start:end]

    def skip_whitespace(self, i):
        ll_chars = self.ll_chars
        while True:
            ch = ll_chars[i]
            if is_whitespace(ch):
                i += 1
            else:
                break
        return i

    def decode_any(self, i):
        i = self.skip_whitespace(i)
        ch = self.ll_chars[i]
        if ch == '"':
            return self.decode_string(i+1)
        elif ch == '[':
            return self.decode_array(i+1)
        elif ch == '{':
            return self.decode_object(i+1)
        elif ch == 'n':
            return self.decode_null(i+1)
        elif ch == 't':
            return self.decode_true(i+1)
        elif ch == 'f':
            return self.decode_false(i+1)
        elif ch == 'I':
            return self.decode_infinity(i+1)
        elif ch == 'N':
            return self.decode_nan(i+1)
        elif ch == '-':
            if self.ll_chars[i+1] == 'I':
                return self.decode_infinity(i+2, sign=-1)
            return self.decode_numeric(i)
        elif ch.isdigit():
            return self.decode_numeric(i)
        else:
            self._raise("No JSON object could be decoded: unexpected '%s' at char %d",
                        ch, i)


    @specialize.arg(1)
    def _raise(self, msg, *args):
        raise oefmt(self.space.w_ValueError, msg, *args)

    def decode_null(self, i):
        if (self.ll_chars[i]   == 'u' and
            self.ll_chars[i+1] == 'l' and
            self.ll_chars[i+2] == 'l'):
            self.pos = i+3
            return self.space.w_None
        self._raise("Error when decoding null at char %d", i)

    def decode_true(self, i):
        if (self.ll_chars[i]   == 'r' and
            self.ll_chars[i+1] == 'u' and
            self.ll_chars[i+2] == 'e'):
            self.pos = i+3
            return self.space.w_True
        self._raise("Error when decoding true at char %d", i)

    def decode_false(self, i):
        if (self.ll_chars[i]   == 'a' and
            self.ll_chars[i+1] == 'l' and
            self.ll_chars[i+2] == 's' and
            self.ll_chars[i+3] == 'e'):
            self.pos = i+4
            return self.space.w_False
        self._raise("Error when decoding false at char %d", i)

    def decode_infinity(self, i, sign=1):
        if (self.ll_chars[i]   == 'n' and
            self.ll_chars[i+1] == 'f' and
            self.ll_chars[i+2] == 'i' and
            self.ll_chars[i+3] == 'n' and
            self.ll_chars[i+4] == 'i' and
            self.ll_chars[i+5] == 't' and
            self.ll_chars[i+6] == 'y'):
            self.pos = i+7
            return self.space.newfloat(rfloat.INFINITY * sign)
        self._raise("Error when decoding Infinity at char %d", i)

    def decode_nan(self, i):
        if (self.ll_chars[i]   == 'a' and
            self.ll_chars[i+1] == 'N'):
            self.pos = i+2
            return self.space.newfloat(rfloat.NAN)
        self._raise("Error when decoding NaN at char %d", i)

    def decode_numeric(self, i):
        start = i
        i, ovf_maybe, intval = self.parse_integer(i)
        #
        # check for the optional fractional part
        ch = self.ll_chars[i]
        if ch == '.':
            if not self.ll_chars[i+1].isdigit():
                self._raise("Expected digit at char %d", i+1)
            return self.decode_float(start)
        elif ch == 'e' or ch == 'E':
            return self.decode_float(start)
        elif ovf_maybe:
            return self.decode_int_slow(start)

        self.pos = i
        return self.intcache.newint(intval)

    def decode_float(self, i):
        from rpython.rlib import rdtoa
        start = rffi.ptradd(self.ll_chars, i)
        floatval = rdtoa.dg_strtod(start, self.end_ptr)
        diff = rffi.cast(rffi.LONG, self.end_ptr[0]) - rffi.cast(rffi.LONG, start)
        self.pos = i + diff
        return self.space.newfloat(floatval)

    def decode_int_slow(self, i):
        start = i
        if self.ll_chars[i] == '-':
            i += 1
        while self.ll_chars[i].isdigit():
            i += 1
        s = self.getslice(start, i)
        self.pos = i
        return self.space.call_function(self.space.w_int, self.space.newtext(s))

    @always_inline
    def parse_integer(self, i):
        "Parse a decimal number with an optional minus sign"
        sign = 1
        # parse the sign
        if self.ll_chars[i] == '-':
            sign = -1
            i += 1
        elif self.ll_chars[i] == '+':
            i += 1
        #
        if self.ll_chars[i] == '0':
            i += 1
            return i, False, 0

        intval = 0
        start = i
        while True:
            ch = self.ll_chars[i]
            if ch.isdigit():
                intval = intval*10 + ord(ch)-ord('0')
                i += 1
            else:
                break
        count = i - start
        if count == 0:
            self._raise("Expected digit at char %d", i)
        # if the number has more digits than OVF_DIGITS, it might have
        # overflowed
        ovf_maybe = (count >= OVF_DIGITS)
        return i, ovf_maybe, sign * intval

    def _raise_control_char_in_string(self, ch, startindex, currindex):
        if ch == '\0':
            self._raise("Unterminated string starting at char %d",
                        startindex - 1)
        else:
            self._raise("Invalid control character at char %d", currindex-1)

    def _raise_object_error(self, ch, start, i):
        if ch == '\0':
            self._raise("Unterminated object starting at char %d", start)
        else:
            self._raise("Unexpected '%s' when decoding object (char %d)",
                        ch, i)

    def decode_surrogate_pair(self, i, highsurr):
        """ uppon enter the following must hold:
              chars[i] == "\\" and chars[i+1] == "u"
        """
        # the possible ValueError is caught by the caller

    def decode_array(self, i):
        w_list = self.space.newlist([])
        start = i
        i = self.skip_whitespace(start)
        if self.ll_chars[i] == ']':
            self.pos = i+1
            return w_list
        #
        while True:
            w_item = self.decode_any(i)
            i = self.pos
            self.space.call_method(w_list, 'append', w_item)
            i = self.skip_whitespace(i)
            ch = self.ll_chars[i]
            i += 1
            if ch == ']':
                self.pos = i
                return w_list
            elif ch == ',':
                pass
            elif ch == '\0':
                self._raise("Unterminated array starting at char %d", start)
            else:
                self._raise("Unexpected '%s' when decoding array (char %d)",
                            ch, i-1)

    def decode_any_context(self, i, context):
        i = self.skip_whitespace(i)
        ch = self.ll_chars[i]
        if ch == '"':
            return self.decode_string(i+1, context)
        return self.decode_any(i)

    def decode_object(self, i):
        start = i

        i = self.skip_whitespace(i)
        if self.ll_chars[i] == '}':
            self.pos = i+1
            return self.space.newdict()

        if self.scratch:
            values_w = self.scratch.pop()
        else:
            values_w = [None] * self.DEFAULT_SIZE_SCRATCH
        nextindex = 0
        currmap = self.startmap
        while True:
            # parse a key: value
            currmap = self.decode_key(i, currmap)
            i = self.skip_whitespace(self.pos)
            ch = self.ll_chars[i]
            if ch != ':':
                self._raise("No ':' found at char %d", i)
            i += 1

            w_value = self.decode_any_context(i, currmap)

            if nextindex == len(values_w):  # full
                values_w = values_w + [None] * len(values_w)  # double
            values_w[nextindex] = w_value
            nextindex += 1
            i = self.skip_whitespace(self.pos)
            ch = self.ll_chars[i]
            i += 1
            if ch == '}':
                self.pos = i
                if currmap.is_blocked():
                    currmap.instantiation_count += 1
                    self.scratch.append(values_w)  # can reuse next time
                    dict_w = self._switch_to_dict(currmap, values_w, nextindex)
                    return self._create_dict(dict_w)
                self.scratch.append(values_w)  # can reuse next time
                values_w = values_w[:nextindex]
                currmap.instantiation_count += 1
                w_res = self._create_dict_map(values_w, currmap)
                if currmap.state != MapBase.USEFUL:
                    self.unclear_objects.append(w_res)
                return w_res
            elif ch == ',':
                i = self.skip_whitespace(i)
                if currmap.is_blocked():
                    currmap.instantiation_count += 1
                    self.scratch.append(values_w)  # can reuse next time
                    dict_w = self._switch_to_dict(currmap, values_w, nextindex)
                    return self.decode_object_dict(i, start, dict_w)
            else:
                self._raise_object_error(ch, start, i - 1)

    def _create_dict_map(self, values_w, jsonmap):
        from pypy.objspace.std.jsondict import from_values_and_jsonmap
        return from_values_and_jsonmap(self.space, values_w, jsonmap)

    def _devolve_jsonmap_dict(self, w_dict):
        from pypy.objspace.std.jsondict import devolve_jsonmap_dict
        devolve_jsonmap_dict(w_dict)

    def _get_jsonmap_from_dict(self, w_dict):
        from pypy.objspace.std.jsondict import get_jsonmap_from_dict
        return get_jsonmap_from_dict(w_dict)

    def _switch_to_dict(self, currmap, values_w, nextindex):
        dict_w = self._create_empty_dict()
        index = nextindex - 1
        while isinstance(currmap, JSONMap):
            dict_w[currmap.w_key] = values_w[index]
            index -= 1
            currmap = currmap.prev
        assert len(dict_w) == nextindex
        return dict_w

    def decode_object_dict(self, i, start, dict_w):
        while True:
            # parse a key: value
            w_key = self.decode_key_string(i)
            i = self.skip_whitespace(self.pos)
            ch = self.ll_chars[i]
            if ch != ':':
                self._raise("No ':' found at char %d", i)
            i += 1

            w_value = self.decode_any(i)
            dict_w[w_key] = w_value
            i = self.skip_whitespace(self.pos)
            ch = self.ll_chars[i]
            i += 1
            if ch == '}':
                self.pos = i
                return self._create_dict(dict_w)
            elif ch == ',':
                i = self.skip_whitespace(i)
            else:
                self._raise_object_error(ch, start, i - 1)

    def decode_string_uncached(self, i):
        start = i
        ll_chars = self.ll_chars
        nonascii, i = simd.find_end_of_string_no_hash(ll_chars, i, len(self.s))
        ch = ll_chars[i]
        if ch == '\\':
            self.pos = i
            return self.decode_string_escaped(start, nonascii)
        if ch < '\x20':
            self._raise_control_char_in_string(ch, start, i)
        else:
            assert ch == '"'

        self.pos = i + 1
        return self._create_string_wrapped(start, i, nonascii)

    def _create_string_wrapped(self, start, end, nonascii):
        content = self.getslice(start, end)
        if nonascii:
            # contains non-ascii chars, we need to check that it's valid utf-8
            lgt = unicodehelper.check_utf8_or_raise(self.space,
                                                          content)
        else:
            lgt = end - start
        return self.space.newutf8(content, lgt)

    def _create_dict(self, d):
        from pypy.objspace.std.dictmultiobject import from_unicode_key_dict
        return from_unicode_key_dict(self.space, d)

    def _create_empty_dict(self):
        from pypy.objspace.std.dictmultiobject import create_empty_unicode_key_dict
        return create_empty_unicode_key_dict(self.space)

    def decode_string_escaped(self, start, nonascii):
        i = self.pos
        builder = StringBuilder((i - start) * 2) # just an estimate
        assert start >= 0
        assert i >= 0
        builder.append_slice(self.s, start, i)
        while True:
            ch = self.ll_chars[i]
            i += 1
            if ch == '"':
                content_utf8 = builder.build()
                length = unicodehelper.check_utf8_or_raise(self.space,
                                                           content_utf8)
                self.pos = i
                return self.space.newutf8(content_utf8, length)
            elif ch == '\\':
                i = self.decode_escape_sequence_to_utf8(i, builder)
            elif ch < '\x20':
                self._raise_control_char_in_string(ch, start, i)
            else:
                builder.append(ch)

    def decode_escape_sequence_to_utf8(self, i, stringbuilder):
        ch = self.ll_chars[i]
        i += 1
        put = stringbuilder.append
        if ch == '\\':  put('\\')
        elif ch == '"': put('"' )
        elif ch == '/': put('/' )
        elif ch == 'b': put('\b')
        elif ch == 'f': put('\f')
        elif ch == 'n': put('\n')
        elif ch == 'r': put('\r')
        elif ch == 't': put('\t')
        elif ch == 'u':
            # may be a suggorate pair
            return self.decode_escape_sequence_unicode(i, stringbuilder)
        else:
            self._raise("Invalid \\escape: %s (char %d)", ch, i-1)
        return i

    def _get_int_val_from_hex4(self, i):
        ll_chars = self.ll_chars
        res = 0
        for i in range(i, i + 4):
            ch = ord(ll_chars[i])
            if ord('a') <= ch <= ord('f'):
                digit = ch - ord('a') + 10
            elif ord('A') <= ch <= ord('F'):
                digit = ch - ord('A') + 10
            elif ord('0') <= ch <= ord('9'):
                digit = ch - ord('0')
            else:
                raise ValueError
            res = (res << 4) + digit
        return res

    def decode_escape_sequence_unicode(self, i, builder):
        # at this point we are just after the 'u' of the \u1234 sequence.
        start = i
        i += 4
        try:
            val = self._get_int_val_from_hex4(start)
            if (0xd800 <= val <= 0xdbff and
                    self.ll_chars[i] == '\\' and self.ll_chars[i+1] == 'u'):
                lowsurr = self._get_int_val_from_hex4(i + 2)
                if 0xdc00 <= lowsurr <= 0xdfff:
                    # decode surrogate pair
                    val = 0x10000 + (((val - 0xd800) << 10) |
                                     (lowsurr - 0xdc00))
                    i += 6
        except ValueError:
            self._raise("Invalid \uXXXX escape (char %d)", i-1)
            return # help the annotator to know that we'll never go beyond
                   # this point
        #
        utf8_ch = rutf8.unichr_as_utf8(r_uint(val), allow_surrogates=True)
        builder.append(utf8_ch)
        return i


    def decode_string(self, i, context=None):
        ll_chars = self.ll_chars
        start = i
        ch = ll_chars[i]
        if ch == '"':
            self.pos = i + 1
            return self.w_empty_string # surprisingly common

        cache = True
        if context is not None:
            context.decoded_strings += 1
            if not context.should_cache():
                cache = False
        if len(self.s) < self.MIN_SIZE_FOR_STRING_CACHE:
            cache = False

        if not cache:
            return self.decode_string_uncached(i)

        strhash, nonascii, i = simd.find_end_of_string(ll_chars, i, len(self.s))
        ch = ll_chars[i]
        if ch == '\\':
            self.pos = i
            return self.decode_string_escaped(start, nonascii)
        if ch < '\x20':
            self._raise_control_char_in_string(ch, start, i)
        else:
            assert ch == '"'

        self.pos = i + 1

        length = i - start
        strhash ^= length

        # check cache first:
        try:
            entry = self.cache_wrapped[strhash]
        except KeyError:
            w_res = self._create_string_wrapped(start, i, nonascii)
            # only add *some* strings to the cache, because keeping them all is
            # way too expensive
            if (context is not None and context.decoded_strings < 200) or strhash in self.lru_cache:
                entry = WrappedCacheEntry(
                        self.getslice(start, start + length), w_res)
                self.cache_wrapped[strhash] = entry
            else:
                self.lru_cache[self.lru_index] = strhash
                self.lru_index = (self.lru_index + 1) & self.LRU_MASK
            return w_res
        if not _compare_cache_entry(self.space, entry.repr, ll_chars, start, length):
            # hopefully rare
            return self._create_string_wrapped(start, i, nonascii)
        if context is not None:
            context.cache_hits += 1
        return entry.w_uni

    def decode_key(self, i, currmap):
        newmap = self._decode_key(i, currmap)
        currmap.observe_transition(newmap)
        return newmap

    def _decode_key(self, i, currmap):
        ll_chars = self.ll_chars
        nextmap = currmap.fast_path_key_parse(self, i)
        if nextmap is not None:
            return nextmap

        start = i
        ch = ll_chars[i]
        if ch != '"':
            self._raise("Key name must be string at char %d", i)
        i += 1
        w_key = self._decode_key_string(i)
        return currmap.get_next(w_key, self.s, start, self.pos)

    def _decode_key_string(self, i):
        ll_chars = self.ll_chars
        start = i

        strhash, nonascii, i = simd.find_end_of_string(ll_chars, i, len(self.s))

        ch = ll_chars[i]
        if ch == '\\':
            self.pos = i
            w_key = self.decode_string_escaped(start, nonascii)
            return w_key
        if ch < '\x20':
            self._raise_control_char_in_string(ch, start, i)
        length = i - start
        strhash ^= length
        self.pos = i + 1
        # check cache first:
        try:
            entry = self.cache[strhash]
        except KeyError:
            w_res = self._create_string_wrapped(start, i, nonascii)
            entry = WrappedCacheEntry(
                    self.getslice(start, start + length), w_res)
            self.cache[strhash] = entry
            return w_res
        if not _compare_cache_entry(self.space, entry.repr, ll_chars, start, length):
            # hopefully rare
            w_res = self._create_string_wrapped(start, i, nonascii)
            print w_res
        else:
            w_res = entry.w_uni
        return w_res

    def decode_key_string(self, i):
        ll_chars = self.ll_chars
        ch = ll_chars[i]
        if ch != '"':
            self._raise("Key name must be string at char %d", i)
        i += 1
        return self._decode_key_string(i)

class WrappedCacheEntry(object):
    def __init__(self, repr, w_uni):
        self.repr = repr
        self.w_uni = w_uni


class MapBase(object):
    # the basic problem we are trying to solve is the following: dicts in
    # json can either be used as objects, or as dictionaries with arbitrary
    # string keys. We want to use maps for the former, but not for the
    # latter. But we don't know in advance which kind of dict is which.

    # Therefore we create "preliminary" maps where we aren't quite sure yet
    # whether they are really useful maps or not. If we see them used often
    # enough, we promote them to "useful" maps, which we will actually
    # instantiate objects with.

    # If we determine that a map is not used often enough, we can turn it
    # into a "blocked" map, which is a point in the map tree where we will
    # switch to regular dicts, when we reach that part of the tree.

    # allowed graph edges or nodes in all_next:
    #    USEFUL -------
    #   /      \       \
    #  v        v       v
    # FRINGE   USEFUL   BLOCKED
    #  |
    #  v
    # PRELIMINARY
    #  |
    #  v
    # PRELIMINARY

    # state transitions:
    #   PRELIMINARY
    #   /   |       \
    #   |   v        v
    #   | FRINGE -> USEFUL
    #   |   |
    #   \   |
    #    v  v
    #   BLOCKED

    # the single_nextmap edge can only be these graph edges:
    #  USEFUL
    #   |
    #   v
    #  USEFUL
    #
    #  FRINGE
    #   |
    #   v
    #  PRELIMINARY
    #   |
    #   v
    #  PRELIMINARY

    USEFUL = 'u'
    PRELIMINARY = 'p'
    FRINGE = 'f' # buffer between PRELIMINARY and USEFUL
    BLOCKED = 'b'

    # tunable parameters
    MAX_FRINGE = 40
    USEFUL_THRESHOLD = 5

    def __init__(self, space):
        self.space = space

        # a single transition is stored in .single_nextmap
        self.single_nextmap = None

        # all_next is only initialized after seeing the *second* transition
        # but then it also contains .single_nextmap
        self.all_next = None # later dict {key: nextmap}

        self.instantiation_count = 0
        self.number_of_leaves = 1

    def get_terminator(self):
        while isinstance(self, JSONMap):
            self = self.prev
        assert isinstance(self, Terminator)
        return self

    def _check_invariants(self):
        if self.all_next:
            for next in self.all_next.itervalues():
                next._check_invariants()
        elif self.single_nextmap:
            self.single_nextmap._check_invariants()

    def get_next(self, w_key, string, start, stop):
        from pypy.objspace.std.dictmultiobject import unicode_hash, unicode_eq
        if isinstance(self, JSONMap):
            assert not self.state == MapBase.BLOCKED
        single_nextmap = self.single_nextmap
        if (single_nextmap is not None and
                single_nextmap.w_key.eq_w(w_key)):
            return single_nextmap

        assert stop >= 0
        assert start >= 0

        if single_nextmap is None:
            # first transition ever seen, don't initialize all_next
            next = self._make_next_map(w_key, string[start:stop])
            self.single_nextmap = next
        else:
            if self.all_next is None:
                self.all_next = objectmodel.r_dict(unicode_eq, unicode_hash,
                  force_non_null=True, simple_hash_eq=True)
                self.all_next[single_nextmap.w_key] = single_nextmap
            else:
                next = self.all_next.get(w_key, None)
                if next is not None:
                    return next
            next = self._make_next_map(w_key, string[start:stop])
            self.all_next[w_key] = next

            # fix number_of_leaves
            self.change_number_of_leaves(1)

        terminator = self.get_terminator()
        terminator.register_potential_fringe(next)
        return next

    def change_number_of_leaves(self, difference):
        parent = self
        while isinstance(parent, JSONMap):
            parent.number_of_leaves += difference
            parent = parent.prev
        parent.number_of_leaves += difference # terminator

    def fast_path_key_parse(self, decoder, position):
        single_nextmap = self.single_nextmap
        if single_nextmap:
            ll_chars = decoder.ll_chars
            assert isinstance(single_nextmap, JSONMap)
            if single_nextmap.key_repr_cmp(ll_chars, position):
                decoder.pos = position + len(single_nextmap.key_repr)
                return single_nextmap

    def observe_transition(self, newmap):
        """ observe a transition from self to newmap.
        This does a few things, including updating the self size estimate with
        the knowledge that one object transitioned from self to newmap.
        also it potentially decides that self should move to state USEFUL."""
        self.instantiation_count += 1
        if isinstance(self, JSONMap) and self.state == MapBase.FRINGE:
            if self.is_useful():
                self.mark_useful()

    def _make_next_map(self, w_key, key_repr):
        return JSONMap(self.space, self, w_key, key_repr)

    def _all_dot(self, output):
        identity = objectmodel.compute_unique_id(self)
        output.append('%s [shape=box%s];' % (identity, self._get_dot_text()))
        if self.all_next:
            for w_key, value in self.all_next.items():
                assert isinstance(value, JSONMap)
                if value is self.single_nextmap:
                    color = ", color=blue"
                else:
                    color = ""
                output.append('%s -> %s [label="%s"%s];' % (
                    identity, objectmodel.compute_unique_id(value), value.w_key._utf8, color))
                value._all_dot(output)
        elif self.single_nextmap is not None:
            value = self.single_nextmap
            output.append('%s -> %s [label="%s", color=blue];' % (
                identity, objectmodel.compute_unique_id(value), value.w_key._utf8))
            value._all_dot(output)


    def _get_dot_text(self):
        return ", label=base"

    def view(self):
        from dotviewer import graphclient
        import pytest
        r = ["digraph G {"]
        self._all_dot(r)
        r.append("}")
        p = pytest.ensuretemp("resilientast").join("temp.dot")
        p.write("\n".join(r))
        graphclient.display_dot_file(str(p))

    def _get_caching_stats(self):
        caching = 0
        num_maps = 1
        if isinstance(self, JSONMap) and self.should_cache() and self.decoded_strings > 200:
            caching += 1

        if self.all_next:
            children = self.all_next.values()
        elif self.single_nextmap:
            children = [self.single_nextmap]
        else:
            children = []
        for child in children:
            a, b = child._get_caching_stats()
            caching += a
            num_maps += b
        return caching, num_maps

class Terminator(MapBase):
    def __init__(self, space):
        MapBase.__init__(self, space)
        self.all_object_count = 0
        self.current_fringe = {}

    def register_potential_fringe(self, prelim):
        prev = prelim.prev
        if (isinstance(prev, Terminator) or
                isinstance(prev, JSONMap) and prev.state == MapBase.USEFUL):
            prelim.state = MapBase.FRINGE

            if len(self.current_fringe) > MapBase.MAX_FRINGE:
                self.cleanup_fringe()
            self.current_fringe[prelim] = None

    def cleanup_fringe(self):
        min_fringe = None
        min_avg = 10000000000
        for f in self.current_fringe:
            if f.state == MapBase.FRINGE:
                avg = f.average_instantiation()
                if avg < min_avg:
                    min_avg = avg
                    min_fringe = f
            else:
                for f in self.current_fringe.keys():
                    if f.state != MapBase.FRINGE:
                        del self.current_fringe[f]
                return
        assert min_fringe
        min_fringe.mark_blocked()
        del self.current_fringe[min_fringe]


class JSONMap(MapBase):
    """ A map implementation to speed up parsing """

    def __init__(self, space, prev, w_key, key_repr):
        MapBase.__init__(self, space)

        self.prev = prev
        self.w_key = w_key
        self.key_repr = key_repr

        self.state = MapBase.PRELIMINARY

        # key decoding stats
        self.decoded_strings = 0
        self.cache_hits = 0

        # for jsondict support
        self.key_to_index = None
        self.keys_in_order = None
        self.strategy_instance = None

    @jit.elidable
    def get_terminator(self):
        while isinstance(self, JSONMap):
            self = self.prev
        assert isinstance(self, Terminator)
        return self

    def _check_invariants(self):
        assert self.state in (
            MapBase.USEFUL,
            MapBase.PRELIMINARY,
            MapBase.FRINGE,
            MapBase.BLOCKED,
        )

        prev = self.prev
        if isinstance(prev, JSONMap):
            prevstate = prev.state
        else:
            prevstate = MapBase.USEFUL

        if prevstate == MapBase.USEFUL:
            assert self.state != MapBase.PRELIMINARY
        elif prevstate == MapBase.PRELIMINARY:
            assert self.state == MapBase.PRELIMINARY
        elif prevstate == MapBase.FRINGE:
            assert self.state == MapBase.PRELIMINARY
        else:
            # if prevstate is BLOCKED, we shouldn't have recursed here!
            assert False, "should be unreachable"

        if self.state == MapBase.BLOCKED:
            assert self.single_nextmap is None
            assert self.all_next is None

        MapBase._check_invariants(self)

    def mark_useful(self):
        # mark self as useful, and also the most commonly instantiated
        # children, recursively
        assert self.state in (MapBase.FRINGE, MapBase.PRELIMINARY)
        self.state = MapBase.USEFUL
        maxchild = self.single_nextmap
        if self.all_next is not None:
            for child in self.all_next.itervalues():
                if child.instantiation_count > maxchild.instantiation_count:
                    maxchild = child
        if maxchild is not None:
            maxchild.mark_useful()
            if self.all_next:
                terminator = self.get_terminator()
                for child in self.all_next.itervalues():
                    if child is not maxchild:
                        terminator.register_potential_fringe(child)
                self.single_nextmap = maxchild

    def mark_blocked(self):
        self.state = MapBase.BLOCKED
        if self.all_next:
            for next in self.all_next.itervalues():
                next.mark_blocked()
        elif self.single_nextmap:
            self.single_nextmap.mark_blocked()
        self.single_nextmap = None
        self.all_next = None
        self.change_number_of_leaves(-self.number_of_leaves + 1)

    def is_blocked(self):
        return self.state == MapBase.BLOCKED

    def average_instantiation(self):
        return self.instantiation_count / float(self.number_of_leaves)

    def is_useful(self):
        return self.average_instantiation() > self.USEFUL_THRESHOLD

    def should_cache(self):
        return not (self.decoded_strings > 200 and self.cache_hits * 4 < self.decoded_strings)

    def key_repr_cmp(self, ll_chars, i):
        for j, c in enumerate(self.key_repr):
            if ll_chars[i] != c:
                return False
            i += 1
        return True

    # _____________________________________________________
    # methods for JsonDictStrategy

    @jit.elidable
    def get_index(self, w_key):
        from pypy.objspace.std.unicodeobject import W_UnicodeObject
        assert isinstance(w_key, W_UnicodeObject)
        return self.get_key_to_index().get(w_key, -1)

    def get_key_to_index(self):
        from pypy.objspace.std.dictmultiobject import unicode_hash, unicode_eq
        key_to_index = self.key_to_index
        if key_to_index is None:
            key_to_index = self.key_to_index = objectmodel.r_dict(unicode_eq, unicode_hash,
                  force_non_null=True, simple_hash_eq=True)
            # compute depth
            curr = self
            depth = 0
            while True:
                depth += 1
                curr = curr.prev
                if not isinstance(curr, JSONMap):
                    break

            curr = self
            while depth:
                depth -= 1
                key_to_index[curr.w_key] = depth
                curr = curr.prev
                if not isinstance(curr, JSONMap):
                    break
        return key_to_index

    def get_keys_in_order(self):
        keys_in_order = self.keys_in_order
        if keys_in_order is None:
            key_to_index = self.get_key_to_index()
            keys_in_order = self.keys_in_order = [None] * len(key_to_index)
            for w_key, index in key_to_index.iteritems():
                keys_in_order[index] = w_key
        return keys_in_order

    # _____________________________________________________

    def _get_dot_text(self):
        if self.all_next is None:
            l = int(self.single_nextmap is not None)
        else:
            l = len(self.all_next) + 1
        extra = ""
        if self.decoded_strings:
            extra = "\\n%s/%s (%s%%)" % (self.cache_hits, self.decoded_strings, self.cache_hits/float(self.decoded_strings))
        res = ', label="#%s\\nchildren: %s%s"' % (self.instantiation_count, l, extra)
        if self.state == MapBase.BLOCKED:
            res += ", fillcolor=lightsalmon"
        if self.state == MapBase.FRINGE:
            res += ", fillcolor=lightgray"
        if self.state == MapBase.PRELIMINARY:
            res += ", fillcolor=lightslategray"
        return res


def loads(space, w_s):
    if space.isinstance_w(w_s, space.w_unicode):
        raise oefmt(space.w_TypeError,
                    "Expected utf8-encoded str, got unicode")
    s = space.bytes_w(w_s)
    decoder = JSONDecoder(space, s)
    try:
        w_res = decoder.decode_any(0)
        i = decoder.skip_whitespace(decoder.pos)
        if i < len(s):
            start = i
            end = len(s) - 1
            raise oefmt(space.w_ValueError,
                        "Extra data: char %d - %d", start, end)
        return w_res
    finally:
        decoder.close()

