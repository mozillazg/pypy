from pypy.rlib import rope

class RopeString(object):
    def __init__ (self, s):
        self._node = rope.LiteralStringNode(s)
    
    def __len__ (self):
        return self._node.length()

    def __getitem__ (self, index):
        return self._node.getchar(index)
    
    def __eq__ (self, other):
        return rope.eq (self._node, rope.LiteralStringNode(other))
    
    def __add__ (self, other):
        result = RopeString('')
        result._node = self._node + other._node
	return result
    
    def __mul__ (self, n):
        result = RopeString('')
        result._node = rope.multiply(self._node, n)
        return result
    
    def __rmul__ (self, n):
        return self * n

class RopeUnicode(object):
    pass
