
from pypy.rlib.objectmodel import compute_identity_hash
from pypy.rlib.jit_hooks import _cast_to_gcref
from pypy.rpython.lltypesystem import lltype, llmemory

# Placeholder constants

FREE = -1
DUMMY = -2

TP = lltype.GcArray(lltype.Struct('dictentry',
                                  ('key', lltype.Signed),
                                  ('value', llmemory.GCREF)))
MAIN_TP = lltype.GcArray(lltype.Signed)

class Dict(object):
    'Space efficient dictionary with fast iteration and cheap resizes.'

    def _lookup(self, key, hashvalue):
        'Same lookup logic as currently used in real dicts'
        assert self.filled < len(self.indices)   # At least one open slot
        freeslot = -1
        PERTURB_SHIFT = 5
        if hashvalue < 0:
            perturb = -hashvalue
        else:
            perturb = hashvalue
        n = len(self.indices)
        i = perturb & (n-1)
        while True:
            index = self.indices[i]
            if index == FREE:
                return (FREE, i) if freeslot == -1 else (DUMMY, freeslot)
            elif index == DUMMY:
                freeslot = i
            elif self.values[index].key == key:
                return (index, i)
            i = 5 * i + perturb + 1
            i = i & (n-1)
            perturb >>= PERTURB_SHIFT
    _lookup._always_inline_ = True

    def _make_index(self, n):
        'New sequence of indices using the smallest possible datatype'
        #if n <= 2**7: return array.array('b', [FREE]) * n       # signed char
        #if n <= 2**15: return array.array('h', [FREE]) * n      # signed short
        #if n <= 2**31: return array.array('l', [FREE]) * n      # signed long
        return lltype.malloc(MAIN_TP, n)

    def _resize(self, n):
        '''Reindex the existing hash/key/value entries.
           Entries do not get moved, they only get new indices.
           No calls are made to hash() or __eq__().

        '''
        new_size = 8
        while new_size < n:
            new_size <<= 1
        n = new_size
        self.indices = self._make_index(n)
        PERTURB_SHIFT = 5
        for index, hashvalue in enumerate(self.hashlist):
            if hashvalue < 0:
                perturb = -hashvalue
            else:
                perturb = hashvalue
            i = hashvalue & (n-1)
            while True:
                if self.indices[i] == FREE:
                    break
                i = 5 * i + perturb + 1
                i = i & (n-1)
                perturb >>= PERTURB_SHIFT
            self.indices[i] = index
        self.filled = self.used
        old_values = self.values
        self.values = lltype.malloc(TP, new_size * 2 / 3)
        for i in range(self.used):
            self.values[i].key = old_values[i].key
            self.values[i].value = old_values[i].value

    def clear(self):
        self.indices = self._make_index(8)
        self.values = lltype.malloc(TP, 8 * 3 / 2)
        self.used = 0
        self.filled = 0                                         # used + dummies

    def __init__(self):
        self.clear()

    def __getitem__(self, key):
        hashvalue = hash(key)
        index, i = self._lookup(key, hashvalue)
        if index < 0:
            raise KeyError(key)
        return self.valuelist[index]

    def __setitem__(self, key, value):
        hashvalue = key # hash
        index, i = self._lookup(key, hashvalue)
        if index < 0:
            self.indices[i] = self.used
            self.values[self.used].key = key
            self.values[self.used].value = _cast_to_gcref(value)
            self.used += 1
            if index == FREE:
                self.filled += 1
                if self.filled * 3 > len(self.indices) * 2:
                    self._resize(4 * self.__len__())
        else:
            self.valuelist[index] = value

    def __delitem__(self, key):
        hashvalue = hash(key)
        index, i = self._lookup(key, hashvalue)
        if index < 0:
            raise KeyError(key)
        self.indices[i] = DUMMY
        self.used -= 1
        # If needed, swap with the lastmost entry to avoid leaving a "hole"
        if index != self.used:
            lasthash = self.hashlist[-1]
            lastkey = self.keylist[-1]
            lastvalue = self.valuelist[-1]
            lastindex, j = self._lookup(lastkey, lasthash)
            assert lastindex >= 0 and i != j
            self.indices[j] = index
            self.hashlist[index] = lasthash
            self.keylist[index] = lastkey
            self.valuelist[index] = lastvalue
        # Remove the lastmost entry
        self.hashlist.pop()
        self.keylist.pop()
        self.valuelist.pop()

    def __len__(self):
        return self.used

    def __iter__(self):
        return iter(self.keylist)

    def iterkeys(self):
        return iter(self.keylist)

    def keys(self):
        return list(self.keylist)

    def itervalues(self):
        return iter(self.valuelist)

    def iteritems(self):
        return itertools.izip(self.keylist, self.valuelist)

    def items(self):
        return zip(self.keylist, self.valuelist)

    def __contains__(self, key):
        index, i = self._lookup(key, hash(key))
        return index >= 0

    def get(self, key, default=None):
        'D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None.'
        index, i = self._lookup(key, hash(key))
        return self.valuelist[index] if index >= 0 else default

    def popitem(self):
        ''' D.popitem() -> (k, v), remove and return some (key, value) pair as a
            2-tuple; but raise KeyError if D is empty.
        '''
        try:
            key = self.keylist[-1]
            value = self.valuelist[-1]
        except IndexError:
            raise KeyError( 'popitem(): dictionary is empty')
        del self[key]
        return key, value

    def __repr__(self):
        return 'Dict(%r)' % self.items()

    def show_structure(self):
        'Diagnostic method.  Not part of the API.'
        print '=' * 50
        print self
        print 'Indices:', self.indices
        for i, row in enumerate(zip(self.hashlist, self.keylist, self.valuelist)):
            print i, row
        print '-' * 50


if __name__ == '__main__':
    import sys
    def f():
        if len(sys.argv) > 1:
            d = {}
        else:
            d = Dict()
        class A(object):
            pass
        for i in range(10000000):
            d[i] = A()
    f()
