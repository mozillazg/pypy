from pypy.conftest import gettestobjspace

class AppTestJvm:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('jvm',))
        cls.space = space

    def test_new(self):
        import jvm

        methods = jvm.new('java.lang.Object')
        assert isinstance(methods, list)

        expected_methods = {'getClass', 'notifyAll', 'equals', 'hashCode',
                            'toString', 'notify', 'wait'}

        assert set(methods) == expected_methods

