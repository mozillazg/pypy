from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.error import decompose_valuefmt, get_operrcls2


def test_decompose_valuefmt():
    assert (decompose_valuefmt("abc %s def") ==
            (("abc ", " def"), ('s',)))
    assert (decompose_valuefmt("%s%d%s") ==
            (("", "", "", ""), ('s', 'd', 's')))

def test_get_operrcls2():
    cls, strings = get_operrcls2('abc %s def %d')
    assert strings == ("abc ", " def ", "")
    assert issubclass(cls, OperationError)
    inst = cls("w_type", strings, "hello", 42)
    assert inst._compute_value() == "abc hello def 42"

def test_operationerrfmt():
    operr = operationerrfmt("w_type", "abc %s def %d", "foo", 42)
    assert isinstance(operr, OperationError)
    assert operr.w_type == "w_type"
    assert operr._w_value is None
    assert operr._compute_value() == "abc foo def 42"
