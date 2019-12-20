from pypy.tool.pytest.objspace import gettestobjspace

def test_default_is_dummy_importlib():
    space = gettestobjspace()
    assert space.config.objspace.usemodules._dummy_importlib
    assert not space.config.objspace.usemodules._frozen_importlib
    #
    space = gettestobjspace(usemodules=['_frozen_importlib'])
    assert not space.config.objspace.usemodules._dummy_importlib
    assert space.config.objspace.usemodules._frozen_importlib


class AppTestDummyImportlib:

    def test_import_builtin(self):
        import sys
        import operator
        assert sys.modules['operator'] is operator
        assert operator.add(1, 2) == 3

    def test_import_from_sys_path(self):
        import keyword # this is a module from lib-python
        assert keyword.iskeyword('def')
