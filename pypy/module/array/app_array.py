import operator

if True:
    def initiate(self, initializer):
        if initializer is not None:
            if type(initializer) is str:
                self.fromstring(initializer)
            elif type(initializer) is unicode:
                self.fromunicode(initializer)
            elif type(initializer) is list:
                self.fromlist(initializer)
            else:
                self.extend(initializer)

    def fromunicode(self, ustr):
        """Extends this array with data from the unicode string ustr. The array
        must be a type 'u' array; otherwise a ValueError is raised. Use
        array.fromstring(ustr.encode(...)) to append Unicode data to an array of
        some other type."""
        if not self.typecode == "u":
            raise ValueError(
                          "fromunicode() may only be called on type 'u' arrays")
        # XXX the following probable bug is not emulated:
        # CPython accepts a non-unicode string or a buffer, and then
        # behaves just like fromstring(), except that it strangely truncates
        # string arguments at multiples of the unicode byte size.
        # Let's only accept unicode arguments for now.
        if not isinstance(ustr, unicode):
            raise TypeError("fromunicode() argument should probably be "
                            "a unicode string")
        self._fromsequence(ustr)


    def fromfile(self, f, n):
        """Read n objects from the file object f and append them to the end of
        the array. Also called as read."""
        if not isinstance(f, file):
            raise TypeError("arg1 must be open file")

        size = self.itemsize * n
        print "read"
        item = f.read(size)
        print item
        if len(item) < size:
            n = len(item) % self.itemsize
            if n != 0: item = item[0:-(len(item) % self.itemsize)]
            self.fromstring(item)
            raise EOFError("not enough items in file")
        self.fromstring(item)

        
    def fromlist(self, l):
        """Append items to array from list."""
        if not isinstance(l, list):
            raise TypeError("arg must be list")
        s=len(self)
        try:
            self._fromsequence(l)
        except(OverflowError, TypeError, ValueError):
            self._setlen(s)
            raise


    def tounicode(self):
        """Convert the array to a unicode string. The array must be a type 'u'
        array; otherwise a ValueError is raised. Use array.tostring().decode()
        to obtain a unicode string from an array of some other type."""
        if self.typecode != "u":
            raise ValueError("tounicode() may only be called on type 'u' arrays")
        # XXX performance is not too good
        return u"".join(self.tolist())

    def tofile(self, f):
        """Write all items (as machine values) to the file object f.  Also
        called as write."""
        if not isinstance(f, file):
            raise TypeError("arg must be open file")
        f.write(self.tostring())

    def tostring(self):
        import struct
        s=''
        for i in range(len(self)):
            s+=struct.pack(self.typecode, self[i])
        return s

        
    def __repr__(self):
        if len(self) == 0:
            return "array('%s')" % self.typecode
        elif self.typecode == "c":
            return "array('%s', %s)" % (self.typecode, repr(self.tostring()))
        elif self.typecode == "u":
            return "array('%s', %s)" % (self.typecode, repr(self.tounicode()))
        else:
            return "array('%s', %s)" % (self.typecode, repr(self.tolist()))

    ##### list methods
    
    def count(self, x):
        """Return number of occurences of x in the array."""
        return operator.countOf(self, x)
    def index(self, x):
        """Return index of first occurence of x in the array."""
        return operator.indexOf(self, x)
    
    def remove(self, x):
        """Remove the first occurence of x in the array."""
        self.pop(self.index(x))
        
    def reverse(self):
        """Reverse the order of the items in the array."""
        lst = self.tolist()
        lst.reverse()
        self._setlen(0)
        self.fromlist(lst)

    def insert(self, i, x):
        lst=self.tolist()
        lst.insert(i, x)
        self._setlen(0)
        self.fromlist(lst)

    def __eq__(self, other):
        if not self._isarray(other):
            return NotImplemented
        if self.typecode == 'c':
            return buffer(self) == buffer(other)
        else:
            return self.tolist() == other.tolist()

    def __ne__(self, other):
        if not self._isarray(other):
            return NotImplemented
        if self.typecode == 'c':
            return buffer(self) != buffer(other)
        else:
            return self.tolist() != other.tolist()

    def __lt__(self, other):
        if not self._isarray(other):
            return NotImplemented
        if self.typecode == 'c':
            return buffer(self) < buffer(other)
        else:
            return self.tolist() < other.tolist()

    def __gt__(self, other):
        if not self._isarray(other):
            return NotImplemented
        if self.typecode == 'c':
            return buffer(self) > buffer(other)
        else:
            return self.tolist() > other.tolist()

    def __le__(self, other):
        if not self._isarray(other):
            return NotImplemented
        if self.typecode == 'c':
            return buffer(self) <= buffer(other)
        else:
            return self.tolist() <= other.tolist()

    def __ge__(self, other):
        if not self._isarray(other):
            return NotImplemented
        if self.typecode == 'c':
            return buffer(self) >= buffer(other)
        else:
            return self.tolist() >= other.tolist()

    ##### list protocol

    def __getslice__(self, i, j):
        return self.__getitem__(slice(i, j))

    def __setslice__(self, i, j, x):
        self.__setitem__(slice(i, j), x)

    def __delslice__(self, i, j):
        self.__delitem__(slice(i, j))

    def __contains__(self, item):
        for x in self:
            if x == item:
                return True
        return False

