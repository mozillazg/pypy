from pypy.conftest import gettestobjspace

class AppTestJvm:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('jvm',))
        cls.space = space

    def test_make_instance(self):
        import jvm
        obj = jvm.make_instance('java.lang.Object')

        expected_methods = {'getClass', 'notifyAll', 'equals', 'hashCode',
                            'toString', 'notify', 'wait'}

        for name in expected_methods:
            assert hasattr(obj, name)
            assert name in getattr(obj, name)()

        for name in [m for m in dir(obj) if not m.startswith('_')]:
            assert name in expected_methods

        assert obj._class_name == 'Object'
        assert obj._full_name == 'java.lang.Object'


