from pypy.rlib import rope

class RopeString(object):
    def __init__ (self, str):
        self._node = rope.LiteralStringNode(str)
    
    def __len__ (self):
        return self._node.length()

    def __getitem__ (self, index):
        return self._node.getchar(index)
    
    def __eq__ (self, str):
        return rope.eq (self._node, rope.LiteralStringNode(str))

class RopeUnicode(object):
    pass
