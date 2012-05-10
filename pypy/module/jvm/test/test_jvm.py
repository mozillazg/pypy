
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
