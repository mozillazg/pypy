
def test_base_exc():
    from pypy.tool.compat import BaseException
    assert issubclass(KeyboardInterrupt, BaseException)
    assert issubclass(ValueError, BaseException)
