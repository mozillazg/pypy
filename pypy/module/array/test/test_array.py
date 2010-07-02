from pypy.conftest import gettestobjspace

class AppTestcArray:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('array',))
        cls.w_array = cls.space.appexec([], """():
            import array
            return array.array
        """)

    def test_simple(self):
        a=self.array(10)
        a[5]=7.42
        assert a[5]==7.42


## space.sys.get('modules')

## w_import   = space.builtin.get('__import__')
## w_array  = space.call(w_import, space.newlist([space.wrap('array')]))

## print w_array
## space.appexec([], "(): import array; print array.array(7)")
## print space.appexec([], "(): import array; return array.array(7)")
## space.appexec([], "(): import array; a=array.array(7); print a[2]")
## space.appexec([], "(): import array; a=array.array(7); a[2]=7.42; print a[2]")
