
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
        except:
            print 'FAIL'
        else:
            print 'OK'

    print
