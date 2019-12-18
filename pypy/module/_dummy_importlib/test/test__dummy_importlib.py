from pypy.tool.pytest.objspace import gettestobjspace

def test_default_is_dummy_importlib():
    space = gettestobjspace()
    assert space.config.objspace.usemodules._dummy_importlib
    assert not space.config.objspace.usemodules._frozen_importlib
    #
    space = gettestobjspace(usemodules=['_frozen_importlib'])
    assert not space.config.objspace.usemodules._dummy_importlib
    assert space.config.objspace.usemodules._frozen_importlib
