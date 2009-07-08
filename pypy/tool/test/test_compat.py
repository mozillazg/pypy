
def test_base_exc():
    from pypy.tool.compat import BaseException
    assert KeyboardInterrupt.__mro__[-2] is BaseException
    assert ValueError.__mro__[-2] is BaseException
