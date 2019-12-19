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
        assert sys.__name__ == 'sys'

    def test_import_lib_pypy(self):
        import _structseq
        assert hasattr(_structseq, 'structseq_new')

    def test_import_package(self):
        import collections
        assert hasattr(collections, 'namedtuple')
