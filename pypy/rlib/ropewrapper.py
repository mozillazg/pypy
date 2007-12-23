from pypy.rlib import rope

class RopeString(object):
    def __init__(self, s):
        if isinstance(s, str):
            self._node = rope.LiteralStringNode(s)
	if isinstance(s, rope.LiteralStringNode):
            self._node = s
    
    def __len__(self):
        return self._node.length()

    def __getitem__(self, index):
        return self._node.getchar(index)
    
    def __eq__(self, other):
        return rope.eq(self._node, rope.LiteralStringNode(other))
    
    def __add__(self, other):
        return RopeString(self._node + other._node)
    
    def __mul__(self, n):
        return RopeString(rope.multiply(self._node, n))
    
    def __rmul__(self, n):
        return self * n

class RopeUnicode(object):
    def __init__(self, s):
        if isinstance(s, str):
            self._node = rope.LiteralUnicodeNode(unicode(s))
        if isinstance(s, unicode):
            self._node = rope.LiteralUnicodeNode(s)
        if isinstance(s, rope.LiteralUnicodeNode):
            self._node = s
    
    def __len__(self):
        return self._node.length()
    
    def __getitem__(self, index):
        return self._node.getunichar(index)
    
    def __eq__(self, other):
        return rope.eq(self._node, rope.LiteralUnicodeNode(other))
    
    def __add__(self, other):
        return RopeUnicode(self._node + other._node)
   
    def __mul__(self, n):
        return RopeUnicode(rope.multiply(self._node, n))
    
    def __rmul__(self, n):
        return self * n
