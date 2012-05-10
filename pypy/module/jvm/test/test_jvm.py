from pypy.conftest import gettestobjspace

class AppTestJvm:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('jvm',))
        cls.space = space

#    def test_new(self):
#        import jvm
#
#        to_string, methods = jvm.new('java.lang.Object')
#        assert isinstance(methods, list)
#        assert isinstance(to_string, str)
#
#        expected_methods = {'getClass', 'notifyAll', 'equals', 'hashCode',
#                            'toString', 'notify', 'wait'}
#
#        assert set(methods) == expected_methods
#        assert to_string.startswith('java.lang.Object@')

    def test_new(self):
        import jvm
        s = jvm.new('')
        assert isinstance(s, str)
        assert s == 'java.awt.Point[x=0,y=0]'

