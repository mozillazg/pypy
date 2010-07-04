from pypy.conftest import gettestobjspace

class AppTestSizedArray:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('array',))
        cls.w_sized_array = cls.space.appexec([], """():
            import array
            return array.sized_array
        """)

    def test_simple(self):
        a=self.sized_array(10)
        a[5]=7.42
        assert a[5]==7.42

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

        a=self.array('c')
        raises(TypeError, a.append, 7)
        a.append('h')
        assert a[0] == 'h'
        assert type(a[0]) is str
        assert len(a) == 1

        a=self.array('u')
        raises(TypeError, a.append, 7)
        a.append(unicode('h'))
        assert a[0] == unicode('h')
        assert type(a[0]) is unicode
        assert len(a) == 1

        a=self.array('c', ('a', 'b', 'c'))
        assert a[0]=='a'
        assert a[1]=='b'
        assert a[2]=='c'
        assert len(a) == 3

    def test_value_range(self):
        values=(-129, 128, -128, 127, 0, 255, -1, 256,
                -32768, 32767, -32769, 32768, 65535, 65536,
                -2147483647, -2147483648, 2147483647, 4294967295, 4294967296,
                )
        for tc,ok,pt in (('b',(  -128,    34,   127),  int),
                         ('B',(     0,    23,   255),  int),
                         ('h',(-32768, 30535, 32767),  int),
                         ('H',(     0, 56783, 65535),  int),
                         ('i',(-32768, 30535, 32767),  int),
                         ('I',(     0, 56783, 65535), long),
                         ('l',(-2**32/2, 34, 2**32/2-1),  int),
                         ('L',(0, 3523532, 2**32-1), long),
                         ):
            a=self.array(tc, ok)
            assert len(a) == len(ok)
            for v in ok:
                a.append(v)
            for i,v in enumerate(ok*2):
                assert a[i]==v
                assert type(a[i]) is pt
            for v in ok:
                a[1]=v
                assert a[0]==ok[0]
                assert a[1]==v
                assert a[2]==ok[2]
            assert len(a) == 2*len(ok)
            for v in values:
                try:
                    a[1]=v
                    assert a[0]==ok[0]
                    assert a[1]==v
                    assert a[2]==ok[2]
                except OverflowError:
                    pass

    def test_float(self):
        values=[0, 1, 2.5, -4.25]
        for tc in 'fd':
            a=self.array(tc, values)
            assert len(a)==len(values)
            for i,v in enumerate(values):
                assert a[i]==v
                assert type(a[i]) is float
            a[1]=10.125
            assert a[0]==0
            assert a[1]==10.125
            assert a[2]==2.5
            assert len(a)==len(values)


## space.sys.get('modules')

## w_import   = space.builtin.get('__import__')
## w_array  = space.call(w_import, space.newlist([space.wrap('array')]))

## print w_array
## space.appexec([], "(): import array; print array.array(7)")
## print space.appexec([], "(): import array; return array.array(7)")
## space.appexec([], "(): import array; a=array.array(7); print a[2]")
## space.appexec([], "(): import array; a=array.array(7); a[2]=7.42; print a[2]")
