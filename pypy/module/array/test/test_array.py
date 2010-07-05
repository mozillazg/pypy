from pypy.conftest import gettestobjspace


class AppTestSizedArray:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('array',))
        cls.w_sized_array = cls.space.appexec([], """():
            import array
            return array.sized_array
        """)

    def test_simple(self):
        a = self.sized_array(10)
        a[5] = 7.42
        assert a[5] == 7.42


class AppTestArray:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('array',))
        cls.w_array = cls.space.appexec([], """():
            import array
            return array.array
        """)

    def test_ctor(self):
        raises(TypeError, self.array, 'hi')
        raises(TypeError, self.array, 1)
        raises(ValueError, self.array, 'q')

        a = self.array('c')
        raises(TypeError, a.append, 7)
        a.append('h')
        assert a[0] == 'h'
        assert type(a[0]) is str
        assert len(a) == 1

        a = self.array('u')
        raises(TypeError, a.append, 7)
        a.append(unicode('h'))
        assert a[0] == unicode('h')
        assert type(a[0]) is unicode
        assert len(a) == 1

        a = self.array('c', ('a', 'b', 'c'))
        assert a[0] == 'a'
        assert a[1] == 'b'
        assert a[2] == 'c'
        assert len(a) == 3

    def test_value_range(self):
        values = (-129, 128, -128, 127, 0, 255, -1, 256,
                  -32768, 32767, -32769, 32768, 65535, 65536,
                  -2147483647, -2147483648, 2147483647, 4294967295, 4294967296,
                  )
        for bb in (8, 16, 32, 64, 128, 256, 512, 1024):
            for b in (bb - 1, bb, bb + 1):
                values += (2 ** b, 2 ** b + 1, 2 ** b - 1,
                           -2 ** b, -2 ** b + 1, -2 ** b - 1)

        for tc, ok, pt in (('b', (  -128,    34,   127),  int),
                           ('B', (     0,    23,   255),  int),
                           ('h', (-32768, 30535, 32767),  int),
                           ('H', (     0, 56783, 65535),  int),
                           ('i', (-32768, 30535, 32767),  int),
                           ('I', (     0, 56783, 65535), long),
                           ('l', (-2 ** 32 / 2, 34, 2 ** 32 / 2 - 1),  int),
                           ('L', (0, 3523532, 2 ** 32 - 1), long),
                           ):
            a = self.array(tc, ok)
            assert len(a) == len(ok)
            for v in ok:
                a.append(v)
            for i, v in enumerate(ok * 2):
                assert a[i] == v
                assert type(a[i]) is pt
            for v in ok:
                a[1] = v
                assert a[0] == ok[0]
                assert a[1] == v
                assert a[2] == ok[2]
            assert len(a) == 2 * len(ok)
            for v in values:
                try:
                    a[1] = v
                    assert a[0] == ok[0]
                    assert a[1] == v
                    assert a[2] == ok[2]
                except OverflowError:
                    pass

    def test_float(self):
        values = [0, 1, 2.5, -4.25]
        for tc in 'fd':
            a = self.array(tc, values)
            assert len(a) == len(values)
            for i, v in enumerate(values):
                assert a[i] == v
                assert type(a[i]) is float
            a[1] = 10.125
            assert a[0] == 0
            assert a[1] == 10.125
            assert a[2] == 2.5
            assert len(a) == len(values)

    def test_itemsize(self):
        for t in 'cbB': assert(self.array(t).itemsize >= 1)
        for t in 'uhHiI': assert(self.array(t).itemsize >= 2)
        for t in 'lLf': assert(self.array(t).itemsize >= 4)
        for t in 'd': assert(self.array(t).itemsize >= 8)

        inttypes = 'bhil'
        for t in inttypes:
            a = self.array(t, [1, 2, 3])
            b = a.itemsize
            for v in (-2 ** (8 * b) / 2, 2 ** (8 * b) / 2 - 1):
                a[1] = v
                assert a[0] == 1 and a[1] == v and a[2] == 3
            raises(OverflowError, a.append, -2 ** (8 * b) / 2 - 1)
            raises(OverflowError, a.append, 2 ** (8 * b) / 2)

            a = self.array(t.upper(), [1, 2, 3])
            b = a.itemsize
            for v in (0, 2 ** (8 * b) - 1):
                print b, v
                a[1] = v
                assert a[0] == 1 and a[1] == v and a[2] == 3
            raises(OverflowError, a.append, -1)
            raises(OverflowError, a.append, 2 ** (8 * b))
            
    def test_fromstring(self):
        a = self.array('c')
        a.fromstring('Hi!')
        assert a[0] == 'H' and a[1] == 'i' and a[2] == '!' and len(a) == 3

        for t in 'bBhHiIlLfd':
            a = self.array(t)
            a.fromstring('\x00' * a.itemsize*2)
            assert len(a) == 2 and a[0] == 0 and a[1] == 0
            if a.itemsize > 1:
                raises(ValueError, a.fromstring, '\x00' * (a.itemsize-1))
                raises(ValueError, a.fromstring, '\x00' * (a.itemsize+1))
                raises(ValueError, a.fromstring, '\x00' * (2*a.itemsize-1))
                raises(ValueError, a.fromstring, '\x00' * (2*a.itemsize+1))
            b = self.array(t, '\x00' * a.itemsize*2)
            assert len(b) == 2 and b[0] == 0 and b[1] == 0            

    def test_fromfile(self):
        
        class myfile(object):
            def __init__(self, c, s):
                self.c = c
                self.s = s
            def read(self,n):
                return self.c*min(n,self.s)

        f=myfile('\x00', 20)
        for t in 'bBhHiIlLfd':
            a = self.array(t)
            a.fromfile(f,2)
            assert len(a)==2 and a[0]==0 and a[1]==0

        a = self.array('b')
        a.fromfile(myfile('\x01', 20),2)
        assert len(a)==2 and a[0]==1 and a[1]==1

        a = self.array('h')
        a.fromfile(myfile('\x01', 20),2)
        assert len(a)==2 and a[0]==257 and a[1]==257

        for i in (0,1):
            a = self.array('h')
            raises(EOFError, a.fromfile, myfile('\x01', 2+i),2)
            assert len(a)==1 and a[0]==257


    def test_fromlist(self):
        a = self.array('b')
        raises(OverflowError, a.fromlist, [1, 2, 400])
        assert len(a) == 0

        raises(OverflowError, a.extend, [1, 2, 400])
        assert len(a) == 2 and a[0] == 1 and a[1] == 2

        raises(OverflowError, self.array, 'b', [1, 2, 400])

        a = self.array('b', [1, 2])
        assert len(a) == 2 and a[0] == 1 and a[1] == 2

    def test_fromunicode(self):
        raises(ValueError, self.array('i').fromunicode, unicode('hi'))
        a = self.array('u')
        a.fromunicode(unicode('hi'))
        assert len(a) == 2 and a[0] == 'h' and a[1]=='i'

        b = self.array('u', unicode('hi'))
        assert len(b) == 2 and b[0] == 'h' and b[1]=='i'
        
