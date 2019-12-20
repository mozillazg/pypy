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

    def test_no_frozen_importlib(self):
        raises(ImportError, "import _frozen_importlib")

    def test_import_builtin(self):
        import sys
        import operator
        assert sys.modules['operator'] is operator
        assert operator.add(1, 2) == 3

    def test_import_from_sys_path(self):
        import keyword # this is a module from lib-python
        assert keyword.iskeyword('def')

    def test_error_message_on_ImportError(self):
        try:
            import i_dont_exist
        except ImportError as e:
            message = str(e)
            assert 'i_dont_exist' in message
            assert 'spaceconfig' in message

    def test_dont_import_importlib(self):
        try:
            import imp
        except ImportError as e:
            message = str(e)
            assert message.startswith('Importing importlib and/or imp is not allowed')
        try:
            import importlib
        except ImportError as e:
            message = str(e)
            assert message.startswith('Importing importlib and/or imp is not allowed')


class AppTestNoDummyImportlib:
    spaceconfig = {'usemodules': ['_frozen_importlib']}

    def test_no_dummy_importlib(self):
        try:
            import _dummy_importlib
        except ImportError as e:
            assert 'spaceconfig' not in str(e)
