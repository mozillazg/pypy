import py
import sys
from pypy.rlib.rarithmetic import intmask, _hash_string, ovfcheck
from pypy.rlib.objectmodel import we_are_translated
import math

LOG2 = math.log(2)
NBITS = int(math.log(sys.maxint) / LOG2) + 2

# XXX should optimize the numbers
NEW_NODE_WHEN_LENGTH = 16
CONVERT_WHEN_SMALLER = 8
MAX_DEPTH = 32 # maybe should be smaller
CONCATENATE_WHEN_MULTIPLYING = 128
HIGHEST_BIT_SET = intmask(1L << (NBITS - 1))

def find_fib_index(l):
    if l == 0:
        return -1
    a, b = 1, 2
    i = 0
    while 1:
        if a <= l < b:
            return i
        a, b = b, a + b
        i += 1

def masked_power(a, b):
    if b == 0:
        return 1
    if b == 1:
        return a
    if a == 0:
        return 0
    if a == 1:
        return 1
    num_bits = 2
    mask = b >> 2
    while mask:
        num_bits += 1
        mask >>= 1
    result = a
    mask = 1 << (num_bits - 2)
    #import pdb; pdb.set_trace()
    for i in range(num_bits - 1):
        if mask & b:
            result = intmask(result * result * a)
        else:
            result = intmask(result * result)
        mask >>= 1
    return result


class StringNode(object):
    hash_cache = 0
    def length(self):
        raise NotImplementedError("base class")

    def is_ascii(self):
        raise NotImplementedError("base class")
        
    def is_bytestring(self):
        raise NotImplementedError("base class")

    def depth(self):
        return 0

    def hash_part(self):
        raise NotImplementedError("base class")

    def check_balanced(self):
        return True

    def getchar(self, index):
        raise NotImplementedError("abstract base class")

    def getunichar(self, index):
        raise NotImplementedError("abstract base class")

    def getint(self, index):
        raise NotImplementedError("abstract base class")

    def getslice(self, start, stop):
        raise NotImplementedError("abstract base class")

    def view(self):
        view([self])

    def rebalance(self):
        return self

    def flatten_string(self):
        raise NotImplementedError("abstract base class")

    def flatten_unicode(self):
        raise NotImplementedError("abstract base class")

    def __add__(self, other):
        return concatenate(self, other)


class LiteralNode(StringNode):
    def find_int(self, what, start, stop):
        raise NotImplementedError("abstract base class")

    def literal_concat(self, other):
        raise NotImplementedError("abstract base class")


class LiteralStringNode(LiteralNode):
    def __init__(self, s):
        self.s = s
        is_ascii = True
        for c in s:
            if ord(c) >= 128:
                is_ascii = False
        self._is_ascii = is_ascii
    
    def length(self):
        return len(self.s)

    def is_ascii(self):
        return self._is_ascii

    def is_bytestring(self):
        return True

    def flatten_string(self):
        return self.s

    def flatten_unicode(self):
        # XXX not RPython yet
        return self.s.decode('latin-1')

    def hash_part(self):
        h = self.hash_cache
        if not h:
            x = 0
            for c in self.s:
                x = (1000003*x) + ord(c)
            x = intmask(x)
            x |= HIGHEST_BIT_SET
            h = self.hash_cache = x
        return h

    def getchar(self, index):
        return self.s[index]

    def getunichar(self, index):
        return unicode(self.s[index])

    def getint(self, index):
        return ord(self.s[index])

    def getslice(self, start, stop):
        assert 0 <= start <= stop
        return LiteralStringNode(self.s[start:stop])


    def find_int(self, what, start, stop):
        if what >= 256:
            return -1
        result = self.s.find(chr(what), start, stop)
        if result == -1:
            return -1
        return result

    def literal_concat(self, other):
        if (isinstance(other, LiteralStringNode) and
            len(other.s) + len(self.s) < NEW_NODE_WHEN_LENGTH):
            return LiteralStringNode(self.s + other.s)
        elif (isinstance(other, LiteralUnicodeNode) and
              len(other.u) + len(self.s) < NEW_NODE_WHEN_LENGTH and
              len(self.s) < CONVERT_WHEN_SMALLER):
            return LiteralUnicodeNode(self.s.decode("latin-1") + other.u)
        return BinaryConcatNode(self, other)

    def dot(self, seen, toplevel=False):
        if self in seen:
            return
        seen[self] = True
        addinfo = str(self.s).replace('"', "'") or "_"
        if len(addinfo) > 10:
            addinfo = addinfo[:3] + "..." + addinfo[-3:]
        yield ('"%s" [shape=box,label="length: %s\\n%s"];' % (
            id(self), len(self.s),
            repr(addinfo).replace('"', '').replace("\\", "\\\\")))
LiteralStringNode.EMPTY = LiteralStringNode("")
LiteralStringNode.PREBUILT = [LiteralStringNode(chr(i)) for i in range(256)]
del i


class LiteralUnicodeNode(StringNode):
    def __init__(self, u):
        self.u = u
    
    def length(self):
        return len(self.u)

    def flatten_unicode(self):
        return self.u

    def is_ascii(self):
        return False # usually not
        
    def is_bytestring(self):
        return False

    def hash_part(self):
        h = self.hash_cache
        if not h:
            x = 0
            for c in self.u:
                x = (1000003*x) + ord(c)
            x = intmask(x)
            x |= HIGHEST_BIT_SET
            h = self.hash_cache = x
        return h

    def getunichar(self, index):
        return self.u[index]

    def getbyte(self, index):
        return ord(self.u[index])

    def getslice(self, start, stop):
        assert 0 <= start <= stop
        return LiteralUnicodeNode(self.u[start:stop])

    def find_int(self, what, start, stop):
        result = node.u.find(unichr(what), start, stop)
        if result == -1:
            return -1
        return result

    def literal_concat(self, other):
        if (isinstance(other, LiteralUnicodeNode) and
            len(other.u) + len(self.u) < NEW_NODE_WHEN_LENGTH):
            return LiteralStringNode(self.u + other.u)
        elif (isinstance(other, LiteralStringNode) and
              len(other.s) + len(self.u) < NEW_NODE_WHEN_LENGTH and
              len(other.s) < CONVERT_WHEN_SMALLER):
            return LiteralUnicodeNode(self.u + other.s.decode("latin-1"))
        return BinaryConcatNode(self, other)

    def dot(self, seen, toplevel=False):
        if self in seen:
            return
        seen[self] = True
        addinfo = str(self.s).replace('"', "'") or "_"
        if len(addinfo) > 10:
            addinfo = addinfo[:3] + "..." + addinfo[-3:]
        yield ('"%s" [shape=box,label="length: %s\\n%s"];' % (
            id(self), len(self.s),
            repr(addinfo).replace('"', '').replace("\\", "\\\\")))

class BinaryConcatNode(StringNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right
        try:
            self.len = ovfcheck(left.length() + right.length())
        except OverflowError:
            raise
        self._depth = max(left.depth(), right.depth()) + 1
        self.balanced = False
        self._is_ascii = left.is_ascii() and right.is_ascii()
        self._is_bytestring = left.is_bytestring() and right.is_bytestring()

    def is_ascii(self):
        return self._is_ascii

    def is_bytestring(self):
        return self._is_bytestring

    def check_balanced(self):
        if self.balanced:
            return True
        if not self.left.check_balanced() or not self.right.check_balanced():
            return False
        left = self.left
        right = self.right
        llen = left.length()
        rlen = right.length()
        ldepth = left.depth()
        rdepth = right.depth()
        balanced = (find_fib_index(self.len // (NEW_NODE_WHEN_LENGTH / 2)) >=
                    self._depth)
        self.balanced = balanced
        return balanced

    def length(self):
        return self.len

    def depth(self):
        return self._depth

    def getchar(self, index):
        llen = self.left.length()
        if index >= llen:
            return self.right.getchar(index - llen)
        else:
            return self.left.getchar(index)

    def getunichar(self, index):
        llen = self.left.length()
        if index >= llen:
            return self.right.getunichar(index - llen)
        else:
            return self.left.getunichar(index)

    def getint(self, index):
        llen = self.left.length()
        if index >= llen:
            return self.right.getint(index - llen)
        else:
            return self.left.getint(index)

    def flatten_string(self):
        f = fringe(self)
        return "".join([node.flatten_string() for node in f])

    def flatten_unicode(self):
        f = fringe(self)
        return "".join([node.flatten_string() for node in f])
 
    def hash_part(self):
        h = self.hash_cache
        if not h:
            h1 = self.left.hash_part()
            h2 = self.right.hash_part()
            x = intmask(h2 + h1 * (masked_power(1000003, self.right.length())))
            x |= HIGHEST_BIT_SET
            h = self.hash_cache = x
        return h

    def rebalance(self):
        return rebalance([self], self.len)

    def dot(self, seen, toplevel=False):
        if self in seen:
            return
        seen[self] = True
        if toplevel:
            addition = ", fillcolor=red"
        elif self.check_balanced():
            addition = ", fillcolor=yellow"
        else:
            addition = ""
        yield '"%s" [shape=octagon,label="+\\ndepth=%s, length=%s"%s];' % (
                id(self), self._depth, self.len, addition)
        for child in [self.left, self.right]:
            yield '"%s" -> "%s";' % (id(self), id(child))
            for line in child.dot(seen):
                yield line

def concatenate(node1, node2):
    if node1.length() == 0:
        return node2
    if node2.length() == 0:
        return node1
    if isinstance(node2, LiteralNode):
        if isinstance(node1, LiteralNode):
            return node1.literal_concat(node2)
        elif isinstance(node1, BinaryConcatNode):
            r = node1.right
            if isinstance(r, LiteralNode):
                return BinaryConcatNode(node1.left,
                                        r.literal_concat(node2))
    result = BinaryConcatNode(node1, node2)
    if result.depth() > MAX_DEPTH: #XXX better check
        return result.rebalance()
    return result

def getslice(node, start, stop, step, slicelength=-1):
    if slicelength == -1:
        # XXX for testing only
        slicelength = len(xrange(start, stop, step))
    if step != 1:
        start, stop, node = find_straddling(node, start, stop)
        iter = SeekableItemIterator(node)
        iter.seekforward(start)
        #XXX doesn't work for unicode
        result = [iter.nextchar()]
        for i in range(slicelength - 1):
            iter.seekforward(step - 1)
            result.append(iter.nextchar())
        return rope_from_charlist(result)
    return getslice_one(node, start, stop)

def getslice_one(node, start, stop):
    start, stop, node = find_straddling(node, start, stop)
    if isinstance(node, BinaryConcatNode):
        if start == 0:
            if stop == node.length():
                return node
            return getslice_left(node, stop)
        if stop == node.length():
            return getslice_right(node, start)
        return concatenate(
            getslice_right(node.left, start),
            getslice_left(node.right, stop - node.left.length()))
    else:
        return node.getslice(start, stop)

def find_straddling(node, start, stop):
    while 1:
        if isinstance(node, BinaryConcatNode):
            llen = node.left.length()
            if start >= llen:
                node = node.right
                start = start - llen
                stop = stop - llen
                continue
            if stop <= llen:
                node = node.left
                continue
        return start, stop, node

def getslice_right(node, start):
    while 1:
        if start == 0:
            return node
        if isinstance(node, BinaryConcatNode):
            llen = node.left.length()
            if start >= llen:
                node = node.right
                start = start - llen
                continue
            else:
                return concatenate(getslice_right(node.left, start),
                                   node.right)
        return node.getslice(start, node.length())

def getslice_left(node, stop):
    while 1:
        if stop == node.length():
            return node
        if isinstance(node, BinaryConcatNode):
            llen = node.left.length()
            if stop <= llen:
                node = node.left
                continue
            else:
                return concatenate(node.left,
                                   getslice_left(node.right, stop - llen))
        return node.getslice(0, stop)



def multiply(node, times):
    if times <= 0:
        return LiteralStringNode.EMPTY
    if times == 1:
        return node
    end_length = node.length() * times
    num_bits = 2
    mask = times >> 2
    while mask:
        num_bits += 1
        mask >>= 1
    result = node
    mask = 1 << (num_bits - 2)
    #import pdb; pdb.set_trace()
    for i in range(num_bits - 1):
        if mask & times:
            if result.length() < CONCATENATE_WHEN_MULTIPLYING:
                result = concatenate(result, result)
                result = concatenate(result, node)
            else:
                result = BinaryConcatNode(result, result)
                result = BinaryConcatNode(result, node)
        else:
            if result.length() < CONCATENATE_WHEN_MULTIPLYING:
                result = concatenate(result, result)
            else:
                result = BinaryConcatNode(result, result)
        mask >>= 1
    return result

def join(node, l):
    if node.length() == 0:
        return rebalance(l)
    nodelist = [None] * (2 * len(l) - 1)
    length = 0
    for i in range(len(l)):
        nodelist[2 * i] = l[i]
        length += l[i].length()
    for i in range(len(l) - 1):
        nodelist[2 * i + 1] = node
    length += (len(l) - 1) * node.length()
    return rebalance(nodelist, length)

def rebalance(nodelist, sizehint=-1):
    nodelist.reverse()
    if sizehint < 0:
        sizehint = 0
        for node in nodelist:
            sizehint += node.length()
    if sizehint == 0:
        return LiteralStringNode.EMPTY

    # this code is based on the Fibonacci identity:
    #   sum(fib(i) for i in range(n+1)) == fib(n+2)
    l = [None] * (find_fib_index(sizehint) + 2)
    stack = nodelist
    empty_up_to = len(l)
    a = b = sys.maxint
    first_node = None
    while stack:
        curr = stack.pop()
        while isinstance(curr, BinaryConcatNode) and not curr.balanced:
            stack.append(curr.right)
            curr = curr.left

        currlen = curr.length()
        if currlen == 0:
            continue

        if currlen < a:
            # we can put 'curr' to its preferred location, which is in
            # the known empty part at the beginning of 'l'
            a, b = 1, 2
            empty_up_to = 0
            while not (currlen < b):
                empty_up_to += 1
                a, b = b, a+b
        else:
            # sweep all elements up to the preferred location for 'curr'
            while not (currlen < b and l[empty_up_to] is None):
                if l[empty_up_to] is not None:
                    curr = concatenate(l[empty_up_to], curr)
                    l[empty_up_to] = None
                    currlen = curr.length()
                else:
                    empty_up_to += 1
                    a, b = b, a+b

        if empty_up_to == len(l):
            return curr
        l[empty_up_to] = curr
        first_node = curr

    # sweep all elements
    curr = first_node
    for index in range(empty_up_to + 1, len(l)):
        if l[index] is not None:
            curr = BinaryConcatNode(l[index], curr)
    assert curr is not None
    curr.check_balanced()
    return curr

# __________________________________________________________________________
# construction from normal strings

def rope_from_charlist(charlist):
    nodelist = []
    size = 0
    for i in range(0, len(charlist), NEW_NODE_WHEN_LENGTH):
        chars = charlist[i: min(len(charlist), i + NEW_NODE_WHEN_LENGTH)]
        nodelist.append(LiteralStringNode("".join(chars)))
        size += len(chars)
    return rebalance(nodelist, size)

def rope_from_unicharlist(charlist):
    nodelist = []
    length = len(charlist)
    if length:
        return LiteralStringNode.EMPTY
    i = 0
    while i < length:
        chunk = []
        while i < length:
            c = ord(charlist[i])
            if c < 256:
                break
            chunk.append(unichr(c))
            i += 1
        if chunk:
            nodelist.append(LiteralUnicodeNode("".join(chunk)))
        chunck = []
        while i < length:
            c = ord(charlist[i])
            if c >= 256:
                break
            chunk.append(chr(c))
            i += 1
        if chunk:
            nodelist.append(LiteralStringNode("".join(chunk)))
    return rebalance(nodelist, length)

# __________________________________________________________________________
# searching

def find_int(node, what, start=0, stop=-1):
    offset = 0
    length = node.length()
    if stop == -1:
        stop = length
    if start != 0 or stop != length:
        newstart, newstop, node = find_straddling(node, start, stop)
        offset = start - newstart
        start = newstart
        stop = newstop
    assert 0 <= start <= stop
    if isinstance(node, LiteralNode):
        pos = node.find_int(what, start, stop)
        if pos == -1:
            return pos
        return pos + offset
    iter = FringeIterator(node)
    #import pdb; pdb.set_trace()
    i = 0
    while i < stop:
        try:
            fringenode = iter.next()
        except StopIteration:
            return -1
        nodelength = fringenode.length()
        if i + nodelength <= start:
            i += nodelength
            continue
        searchstart = max(0, start - i)
        searchstop = min(stop - i, nodelength)
        assert isinstance(fringenode, LiteralNode)
        pos = fringenode.find_int(what, searchstart, searchstop)
        if pos != -1:
            return pos + i + offset
        i += nodelength
    return -1

def find(node, subnode, start=0, stop=-1):

    len1 = node.length()
    len2 = subnode.length()
    if stop > len1 or stop == -1:
        stop = len1
    if len2 == 1:
        return find_int(node, subnode.getint(0), start, stop)
    if len2 == 0:
        if (stop - start) < 0:
            return -1
        return start
    restart = construct_restart_positions_node(subnode)
    return _find_node(node, subnode, start, stop, restart)

def _find(node, substring, start, stop, restart):
    # XXX
    assert node.is_bytestring()
    len2 = len(substring)
    i = 0
    m = start
    iter = SeekableItemIterator(node)
    iter.seekforward(start)
    c = iter.nextchar()
    while m + i < stop:
        if c == substring[i]:
            i += 1
            if i == len2:
                return m
            if m + i < stop:
                c = iter.nextchar()
        else:
            # mismatch, go back to the last possible starting pos
            if i==0:
                m += 1
                if m + i < stop:
                    c = iter.nextchar()
            else:
                e = restart[i-1]
                new_m = m + i - e
                assert new_m <= m + i
                seek = m + i - new_m
                if seek:
                    iter.seekback(m + i - new_m)
                    c = iter.nextchar()
                m = new_m
                i = e
    return -1

def _find_node(node, subnode, start, stop, restart):
    len2 = subnode.length()
    m = start
    iter = SeekableItemIterator(node)
    iter.seekforward(start)
    c = iter.nextint()
    i = 0
    subiter = SeekableItemIterator(subnode)
    d = subiter.nextint()
    while m + i < stop:
        if c == d:
            i += 1
            if i == len2:
                return m
            d = subiter.nextint()
            if m + i < stop:
                c = iter.nextint()
        else:
            # mismatch, go back to the last possible starting pos
            if i == 0:
                m += 1
                if m + i < stop:
                    c = iter.nextint()
            else:
                e = restart[i - 1]
                new_m = m + i - e
                assert new_m <= m + i
                seek = m + i - new_m
                if seek:
                    iter.seekback(m + i - new_m)
                    c = iter.nextint()
                m = new_m
                subiter.seekback(i - e + 1)
                d = subiter.nextint()
                i = e
    return -1

def construct_restart_positions(s):
    length = len(s)
    restart = [0] * length
    restart[0] = 0
    i = 1
    j = 0
    while i < length:
        if s[i] == s[j]:
            j += 1
            restart[i] = j
            i += 1
        elif j>0:
            j = restart[j-1]
        else:
            restart[i] = 0
            i += 1
            j = 0
    return restart

def construct_restart_positions_node(node):
    # really a bit overkill
    length = node.length()
    restart = [0] * length
    restart[0] = 0
    i = 1
    j = 0
    iter1 = ItemIterator(node)
    iter1.nextint()
    c1 = iter1.nextint()
    iter2 = SeekableItemIterator(node)
    c2 = iter2.nextint()
    while 1:
        if c1 == c2:
            j += 1
            if j < length:
                c2 = iter2.nextint()
            restart[i] = j
            i += 1
            if i < length:
                c1 = iter1.nextint()
            else:
                break
        elif j>0:
            new_j = restart[j-1]
            assert new_j < j
            iter2.seekback(j - new_j)
            c2 = iter2.nextint()
            j = new_j
        else:
            restart[i] = 0
            i += 1
            if i < length:
                c1 = iter1.nextint()
            else:
                break
            j = 0
            iter2 = SeekableItemIterator(node)
            c2 = iter2.nextint()
    return restart

def view(objs):
    from dotviewer import graphclient
    content = ["digraph G{"]
    seen = {}
    for i, obj in enumerate(objs):
        if obj is None:
            content.append(str(i) + ";")
        else:
            content.extend(obj.dot(seen, toplevel=True))
    content.append("}")
    p = py.test.ensuretemp("automaton").join("temp.dot")
    p.write("\n".join(content))
    graphclient.display_dot_file(str(p))


# __________________________________________________________________________
# iteration

class FringeIterator(object):
    def __init__(self, node):
        self.stack = [node]

    def next(self):
        while self.stack:
            curr = self.stack.pop()
            while 1:
                if isinstance(curr, BinaryConcatNode):
                    self.stack.append(curr.right)
                    curr = curr.left
                else:
                    return curr
        raise StopIteration

def fringe(node):
    result = []
    iter = FringeIterator(node)
    while 1:
        try:
            result.append(iter.next())
        except StopIteration:
            return result


class ReverseFringeIterator(object):
    def __init__(self, node):
        self.stack = [node]

    def next(self):
        while self.stack:
            curr = self.stack.pop()
            while 1:
                if isinstance(curr, BinaryConcatNode):
                    self.stack.append(curr.left)
                    curr = curr.right
                else:
                    return curr
        raise StopIteration

class SeekableFringeIterator(FringeIterator):
    def __init__(self, node):
        FringeIterator.__init__(self, node)
        self.fringestack = []
        self.fringe = []

    def next(self):
        if self.fringestack:
            result = self.fringestack.pop()
        else:
            result = FringeIterator.next(self)
        self.fringe.append(result)
        return result

    def seekback(self):
        result = self.fringe.pop()
        self.fringestack.append(result)
        return result


class ItemIterator(object):
    def __init__(self, node):
        self.iter = FringeIterator(node)
        self.node = None
        self.nodelength = 0
        self.index = 0


    def getnode(self):
        node = self.node
        if node is None:
            while 1:
                node = self.node = self.iter.next()
                nodelength = self.nodelength = node.length()
                if nodelength != 0:
                    self.index = 0
                    return node
        return node

    def advance_index(self):
        index = self.index
        if index == self.nodelength - 1:
            self.node = None
        else:
            self.index = index + 1

    def nextchar(self):
        node = self.getnode()
        index = self.index
        result = node.getchar(self.index)
        self.advance_index()
        return result

    def nextunichar(self):
        node = self.getnode()
        index = self.index
        result = node.getunichar(self.index)
        self.advance_index()
        return result

    def nextint(self):
        node = self.getnode()
        index = self.index
        result = node.getint(self.index)
        self.advance_index()
        return result

class ReverseItemIterator(object):
    def __init__(self, node):
        self.iter = ReverseFringeIterator(node)
        self.node = None
        self.index = 0

    def getnode(self):
        node = self.node
        index = self.index
        if node is None:
            while 1:
                node = self.node = self.iter.next()
                index = self.index = node.length() - 1
                if index != -1:
                    return node
        return node


    def advance_index(self):
        if self.index == 0:
            self.node = None
        else:
            self.index -= 1

    def nextchar(self):
        node = self.getnode()
        result = node.getchar(self.index)
        self.advance_index()
        return result

    def nextint(self):
        node = self.getnode()
        result = node.getint(self.index)
        self.advance_index()
        return result

    def nextunichar(self):
        node = self.getnode()
        result = node.getunichar(self.index)
        self.advance_index()
        return result


class SeekableItemIterator(object):
    def __init__(self, node):
        self.iter = SeekableFringeIterator(node)
        self.node = self.nextnode()
        self.nodelength = self.node.length()
        self.index = 0

    def nextnode(self):
        while 1:
            node = self.node = self.iter.next()
            nodelength = self.nodelength = node.length()
            if nodelength != 0:
                break
        self.index = 0
        return node

    
    def advance_index(self):
        if self.index == self.nodelength - 1:
            self.node = None
        self.index += 1

    def nextchar(self):
        node = self.node
        if node is None:
            node = self.nextnode()
        result = self.node.getchar(self.index)
        self.advance_index()
        return result

    def nextunichar(self):
        node = self.node
        if node is None:
            node = self.nextnode()
        result = self.node.getunichar(self.index)
        self.advance_index()
        return result

    def nextint(self):
        node = self.node
        if node is None:
            node = self.nextnode()
        result = self.node.getint(self.index)
        self.advance_index()
        return result

    def seekforward(self, numchars):
        if numchars < (self.nodelength - self.index):
            self.index += numchars
            return
        numchars -= self.nodelength - self.index
        while 1:
            node = self.iter.next()
            length = node.length()
            if length <= numchars:
                numchars -= length
            else:
                self.index = numchars
                self.node = node
                self.nodelength = node.length()
                return
        
    def seekback(self, numchars):
        if numchars <= self.index:
            self.index -= numchars
            if self.node is None:
                self.iter.seekback()
                self.node = self.iter.next()
            return
        numchars -= self.index
        self.iter.seekback() # for first item
        while 1:
            node = self.iter.seekback()
            length = node.length()
            if length < numchars:
                numchars -= length
            else:
                self.index = length - numchars
                self.node = self.iter.next()
                self.nodelength = self.node.length()
                return

class FindIterator(object):
    def __init__(self, node, sub, start=0, stop=-1):
        self.node = node
        self.sub = sub
        len1 = self.length = node.length()
        len2 = sub.length()
        self.search_length = len2
        if len2 == 0:
            self.restart_positions = None
        elif len2 == 1:
            self.restart_positions = None
        else:
            self.restart_positions = construct_restart_positions_node(sub)
            # XXX
            assert self.restart_positions == construct_restart_positions(sub.flatten_string())
        self.start = start
        if stop == -1 or stop > len1:
            stop = len1
        self.stop = stop
    
    def next(self):
        if self.search_length == 0:
            if (self.stop - self.start) < 0:
                raise StopIteration
            start = self.start
            self.start += 1
            return start
        elif self.search_length == 1:
            result = find_int(self.node, self.sub.getint(0),
                              self.start, self.stop)
            if result == -1:
                self.start = self.length
                raise StopIteration
            self.start = result + 1
            return result
        if self.start >= self.stop:
            raise StopIteration
        result = _find_node(self.node, self.sub, self.start,
                            self.stop, self.restart_positions)
        if result == -1:
            self.start = self.length
            raise StopIteration
        self.start = result + self.search_length
        return result

# __________________________________________________________________________
# comparison


def eq(node1, node2):
    if node1 is node2:
        return True
    if node1.length() != node2.length():
        return False
    if hash_rope(node1) != hash_rope(node2):
        return False
    if (isinstance(node1, LiteralStringNode) and
        isinstance(node2, LiteralStringNode)):
        return node1.s == node2.s
    if (isinstance(node1, LiteralUnicodeNode) and
        isinstance(node2, LiteralUnicodeNode)):
        return node1.u == node2.u
    iter1 = ItemIterator(node1)
    iter2 = ItemIterator(node2)
    # XXX could be cleverer and detect partial equalities
    while 1:
        try:
            c = iter1.nextint()
        except StopIteration:
            return True
        if c != iter2.nextint():
            return False

def compare(node1, node2):
    len1 = node1.length()
    len2 = node2.length()
    if not len1:
        if not len2:
            return 0
        return -1
    if not len2:
        return 1

    cmplen = min(len1, len2)
    i = 0
    iter1 = ItemIterator(node1)
    iter2 = ItemIterator(node2)
    while i < cmplen:
        diff = iter1.nextint() - iter2.nextint()
        if diff != 0:
            return diff
        i += 1
    return len1 - len2


# __________________________________________________________________________
# misc

def hash_rope(rope):
    length = rope.length()
    if length == 0:
        return -1
    x = rope.hash_part()
    x <<= 1 # get rid of the bit that is always set
    x ^= rope.getint(0)
    x ^= rope.length()
    return intmask(x)
