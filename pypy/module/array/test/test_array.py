from pypy.conftest import gettestobjspace
import py


class AppTestSimpleArray:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('array',))
        cls.w_simple_array = cls.space.appexec([], """():
            import array
            return array.simple_array
        """)

    def test_simple(self):
        a = self.simple_array(10)
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
        raises(TypeError, a.append, 'hi')
        a.append('h')
        assert a[0] == 'h'
        assert type(a[0]) is str
        assert len(a) == 1

        a = self.array('u')
        raises(TypeError, a.append, 7)
        raises(TypeError, a.append, u'hi')
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

        f=open('/dev/zero','r')
        for t in 'bBhHiIlLfd':
            a = self.array(t)
            a.fromfile(f,2)
            assert len(a)==2 and a[0]==0 and a[1]==0

        a = self.array('b')
        a._fromfile(myfile('\x01', 20),2)
        assert len(a)==2 and a[0]==1 and a[1]==1

        a = self.array('h')
        a._fromfile(myfile('\x01', 20),2)
        assert len(a)==2 and a[0]==257 and a[1]==257

        for i in (0,1):
            a = self.array('h')
            raises(EOFError, a._fromfile, myfile('\x01', 2+i),2)
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

        a = self.array('b')
        raises(TypeError, a.fromlist, (1, 2, 400))

        raises(OverflowError, a.extend, (1, 2, 400))
        assert len(a) == 2 and a[0] == 1 and a[1] == 2

        raises(TypeError, a.extend, self.array('i',(7,8)))
        assert len(a) == 2 and a[0] == 1 and a[1] == 2

        def gen():
            for i in range(4):
                yield i + 10
        a = self.array('i', gen())
        assert len(a) == 4 and a[2] == 12

        raises(OverflowError, self.array, 'b', (1, 2, 400))

        a = self.array('b', (1, 2))
        assert len(a) == 2 and a[0] == 1 and a[1] == 2

    def test_fromunicode(self):
        raises(ValueError, self.array('i').fromunicode, unicode('hi'))
        a = self.array('u')
        a.fromunicode(unicode('hi'))
        assert len(a) == 2 and a[0] == 'h' and a[1]=='i'

        b = self.array('u', unicode('hi'))
        assert len(b) == 2 and b[0] == 'h' and b[1]=='i'
        
    def test_sequence(self):
        a=self.array('i', [1,2,3,4])
        assert len(a)==4
        assert a[0] == 1 and a[1] == 2 and a[2] == 3 and a[3] == 4
        assert a[-4] == 1 and a[-3] == 2 and a[-2] == 3 and a[-1] == 4
        a[-2]=5
        assert a[0] == 1 and a[1] == 2 and a[2] == 5 and a[3] == 4

        for i in (4, -5): raises(IndexError, a.__getitem__, i)

        b = a[0:2]
        assert len(b) == 2 and b[0] == 1 and b[1] == 2
        b[0]=6
        assert len(b) == 2 and b[0] == 6 and b[1] == 2
        assert a[0] == 1 and a[1] == 2 and a[2] == 5 and a[3] == 4
        assert a.itemsize == b.itemsize

        b = a[0:100]
        assert len(b)==4
        assert b[0] == 1 and b[1] == 2 and b[2] == 5 and b[3] == 4

        l1 = [2 * i + 1 for i in range(10)]
        a1 = self.array('i', l1)
        for start in range(10):
            for stop in range(start, 10):
                for step in range(1,10):
                    l2 = l1[start:stop:step]
                    a2 = a1[start:stop:step]
                    assert len(l2) == len(a2)
                    for i in range(len(l2)): assert l2[i] == a2[i]

        a=self.array('i', [1,2,3,4])
        a[1:3]=self.array('i', [5,6])
        assert len(a)==4
        assert a[0] == 1 and a[1] == 5 and a[2] == 6 and a[3] == 4
        a[0:-1:2]=self.array('i', [7,8])
        assert a[0] == 7 and a[1] == 5 and a[2] == 8 and a[3] == 4

        try:
            a[1:2:4]=self.array('i', [5,6,7])
            assert False
        except ValueError:
            pass

        try:
            a[1:3]=self.array('I', [5,6])
            assert False
        except TypeError:
            pass

        try:
            a[1:3]=[5,6]
            assert False
        except TypeError:
            pass

    def test_toxxx(self):
        a = self.array('i', [1,2,3])
        l  = a.tolist()
        assert type(l) is list and len(l)==3
        assert a[0] == 1 and a[1] == 2 and a[2] == 3

        b = self.array('i', a.tostring())
        assert len(b) == 3 and b[0] == 1 and b[1] == 2 and b[2] == 3

        assert self.array('c', ('h', 'i')).tostring() == 'hi'
        a = self.array('i',[0,0,0])
        assert a.tostring() == '\x00'*3*a.itemsize

        s = self.array('i', [1, 2, 3]).tostring()
        assert '\x00' in s
        assert '\x01' in s
        assert '\x02' in s
        assert '\x03' in s
        a=self.array('i', s)
        assert a[0]==1 and a[1]==2 and a[2]==3

        from struct import unpack
        values = (-129, 128, -128, 127, 0, 255, -1, 256, -32760, 32760)
        s = self.array('i', values).tostring()
        a=unpack('i'*len(values), s)
        assert a==values
                 
        #FXIME: How to test?
        #from cStringIO import StringIO
        #f=StringIO()
        #self.array('c', ('h', 'i')).tofile(f)
        #assert f.getvalue() == 'hi'
        
        raises(ValueError, self.array('i').tounicode)
        assert self.array('u', unicode('hello')).tounicode() == unicode('hello')

    def test_buffer(self):
        assert buffer(self.array('h', 'Hi'))[1] == 'i'

    def test_list_methods(self):
        assert repr(self.array('i')) == "array('i')"
        assert repr(self.array('i', [1, 2, 3])) == "array('i', [1, 2, 3])"
        assert repr(self.array('h')) == "array('h')"
        
        a=self.array('i', [1, 2, 3, 1, 2, 1])
        assert a.count(1) == 3
        assert a.count(2) == 2
        assert a.index(3) == 2
        assert a.index(2) == 1

        a.reverse()
        assert repr(a) == "array('i', [1, 2, 1, 3, 2, 1])"

        if False:
            a.remove(3)
            assert repr(a) == "array('i', [1, 2, 1, 2, 1])"
            a.remove(1)
            assert repr(a) == "array('i', [2, 1, 2, 1])"
        
        

    #FIXME
    #def test_type(self):
    #    for t in 'bBhHiIlLfdcu':
    #        assert type(self.array(t)) is self.array


## class AppTestAppArray(AppTestArray):
##     def setup_class(cls):
##         cls.space = gettestobjspace(usemodules=('array',))
##         cls.w_array = cls.space.appexec([], """():
##             import apparray
##             return apparray.array
##         """)
