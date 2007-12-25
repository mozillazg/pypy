from pypy.rlib import rope

class RopeBaseString(object):
    def __init__(self):
        self._node = None
    
    def __len__(self):
        return self._node.length()
    
    def __rmul__(self, n):
        return self * n
    
    def __hash__(self):
        return rope.hash_rope(self._node)
    
    def __eq__(self):
        pass
    
    def __ne__(self, other):
        return not self == other
    
class RopeStringIterator(object):
    def __init__(self, node):
        self._iter = rope.ItemIterator(node)
    
    def next(self):
        return self._iter.nextchar()
    
    def __iter__():
        return self

class RopeString(RopeBaseString):
    def __init__(self, s):
        if isinstance(s, str):
            self._node = rope.LiteralStringNode(s)
	if isinstance(s, rope.LiteralStringNode):
            self._node = s
        raise NotImplemtedError("don't know about %s" % (s, ))
    
    def __getitem__(self, index):
        return self._node.getchar(index)
    
    def __add__(self, other):
        return RopeString(self._node + other._node)
    
    def __mul__(self, n):
        return RopeString(rope.multiply(self._node, n))
    
    def __eq__(self, other):
        if isinstance(other, RopeBaseString):
            return (rope.eq(self._node, other._node))
        else:
            return rope.eq(self._node, rope.LiteralStringNode(other))    
    
    def __iter__(self):
        return RopeStringIterator(self._node)

class RopeUnicodeIterator(object):
    def __init__(self, node):
        self._iter = rope.ItemIterator(node)
    
    def next(self):
        return self._iter.nextunichar()
    
    def __iter__():
        return self

class RopeUnicode(RopeBaseString):
    def __init__(self, s):
        if isinstance(s, str):
            self._node = rope.LiteralUnicodeNode(unicode(s))
        if isinstance(s, unicode):
            self._node = rope.LiteralUnicodeNode(s)
        if isinstance(s, rope.LiteralUnicodeNode):
            self._node = s
    
    def __getitem__(self, index):
        return self._node.getunichar(index)
    
    def __eq__(self, other):
        if isinstance (other, RopeBaseString):
            return rope.eq(self._node, other._node)
        else:
            return rope.eq(self._node, rope.LiteralUnicodeNode(other))
    
    def __add__(self, other):
        return RopeUnicode(self._node + other._node)
   
    def __mul__(self, n):
        return RopeUnicode(rope.multiply(self._node, n))
    
    def __iter__(self):
        return RopeUnicodeIterator(self._node)
