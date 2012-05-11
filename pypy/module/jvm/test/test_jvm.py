
class AppTestJvm(object):
    def setup_class(cls):
        from pypy.conftest import gettestobjspace
        space = gettestobjspace(usemodules=('jvm',))
        cls.space = space

    def test_new(self):
        import jvm
        POINT = 'java.awt.Point'
        p1 = jvm.new(POINT)
        p2 = jvm.new(POINT, (p1, POINT))
        assert p1 == p1
        assert p1 != p2

    def test_get_methods(self):
        import jvm
        ms = jvm.get_methods('java.lang.Object')
        assert isinstance(ms, dict)
        assert set(ms.keys()) == {'equals',
                                  'getClass',
                                  'hashCode',
                                  'notify',
                                  'notifyAll',
                                  'toString',
                                  'wait'}
        assert len(ms['wait']) == 3

        ms = jvm.get_methods('java.lang.StringBuilder')
        appends = ms['append']
        for ret_type, args in appends:
            assert 'Abstract' not in ret_type

    def test_call_method_equals(self):
        import jvm
        POINT = 'java.awt.Point'
        p1 = jvm.new(POINT)
        p2 = jvm.new(POINT, (p1, POINT))

        (res, tpe) = jvm.call_method(p1, 'equals', (p2, 'java.lang.Object'))
        assert isinstance(tpe, str)
        assert tpe == 'java.lang.Boolean'

    def test_call_method_toString(self):
        import jvm
        p1 = jvm.new('java.awt.Point')
        (res, tpe) = jvm.call_method(p1, 'toString')
        assert tpe == 'java.lang.String'

    def test_unboxing(self):
        import jvm
        p1 = jvm.new('java.awt.Point')
        s, _ = jvm.call_method(p1, 'toString')
        unboxed_str = jvm.unbox(s)
        assert isinstance(unboxed_str, str)
        assert unboxed_str == 'java.awt.Point[x=0,y=0]'

        l, _ = jvm.call_method(s, 'length')
        unboxed_int = jvm.unbox(l)
        assert isinstance(unboxed_int, int)
        assert unboxed_int == len('java.awt.Point[x=0,y=0]')

        b, _ = jvm.call_method(s, 'isEmpty')
        unboxed_bool = jvm.unbox(b)
        assert isinstance(unboxed_bool, bool)
        assert unboxed_bool == False

if __name__ == '__main__':
    tests = AppTestJvm()

    print
    print '=' * 80
    print

    for test_name in [name for name in dir(tests) if name.startswith('test_')]:
        print test_name,
        test_case = getattr(tests, test_name)
        try:
            test_case()
        except Exception:
            print 'FAIL'
        else:
            print 'OK'

    print
