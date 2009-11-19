import py
from pypy.lang.io.parser import parse, IoParser
from pypy.lang.io.model import W_Message, W_Number
from pypy.lang.io.objspace import ObjSpace

space = ObjSpace()
def test_parse_number_token():
    t = parse(space, "4")
    assert isinstance(t, W_Message)
    assert t.name == '4'
    
def test_parse_number_sets_cached_result():
    t = parse(space, "4")
    assert isinstance(t.cached_result, W_Number)
    assert t.cached_result.value == 4
    
def test_parse_hexnumber_token():
    t = parse(space, "0xf")
    assert isinstance(t, W_Message)
    assert t.name == '0xf'
    
def test_parse_hexnumber_sets_cached_result():
    t = parse(space, '0xf')
    assert isinstance(t.cached_result, W_Number)
    assert t.cached_result.value == 15
    
def test_parse_identifier():
    t = parse(space, 'foo')
    assert isinstance(t, W_Message)
    assert t.name == 'foo'
    
def test_parse_string():
    t = parse(space, '"a"')
    assert isinstance(t, W_Message)
    assert t.name == '"a"'
    
def test_parse_string_sets_cached_result():
    t = parse(space, '"a"')
    assert space.w_sequence in t.cached_result.protos
    assert t.cached_result.value == 'a'
    
def test_parse_tripple_quoted_string():
    t = parse(space, '"""a"""')
    assert isinstance(t, W_Message)
    assert t.name == '"""a"""'

def test_parse_tripple_quoted_string_sets_cached_result():
    t = parse(space, '"a"')
    assert space.w_sequence in t.cached_result.protos
    assert t.cached_result.value == 'a'
    
def test_parse_arguments_simple():
    t = parse(space, 'a(1)')
    assert len(t.arguments) == 1
    assert t.arguments[0].name == '1'
    
def test_parse_argument_list():
    t = parse(space, 'a(1, "a", 0xa)')
    assert len(t.arguments) == 3
    assert t.arguments[0].name == '1'
    assert t.arguments[1].name == '"a"'
    assert t.arguments[2].name == '0xa'
    
def test_parse_message_chain():
    t = parse(space, 'a 1')
    assert isinstance(t, W_Message)
    assert t.name == 'a'
    next = t.next
    assert isinstance(next, W_Message)
    assert next.name == '1'
    assert next.cached_result.value == 1
    
def test_parse_message_chain_with_arguments():
    t = parse(space, 'a("foo", "bar") 1')
    assert isinstance(t, W_Message)
    assert t.name == 'a'
    next = t.next
    assert isinstance(next, W_Message)
    assert next.name == '1'
    assert next.cached_result.value == 1
    
def test_parse_empty_string_produces_nil_message():
    t = parse(space, '')
    assert isinstance(t, W_Message)
    assert t.name == 'nil'
    
def test_parser_sets_line_and_char_no_on_message():
    py.test.skip("Not implemented yet")
    
def test_parse_only_terminator():
    t = parse(space, ';')
    assert isinstance(t, W_Message)
    assert t.name == 'nil'
    
def test_parse_only_terminator2():
    t = parse(space, """\n""")
    assert isinstance(t, W_Message)
    assert t.name == 'nil'

def test_parse_terminator_between_messages_appends_terminator_message():
    t = parse(space, 'a ; b')

    assert isinstance(t, W_Message)
    assert t.name == 'a'
    t1 = t.next
    
    assert isinstance(t1, W_Message)
    assert t1.name == ';'    
    t2 = t1.next
    
    assert isinstance(t2, W_Message)
    assert t2.name == 'b'
    
def test_parse_terminator_between_messages_appends_terminator_message2():
    t = parse(space, 'a ;;;;;; ; b')

    assert isinstance(t, W_Message)
    assert t.name == 'a'
    t1 = t.next

    assert isinstance(t1, W_Message)
    assert t1.name == ';'    
    t2 = t1.next

    assert isinstance(t2, W_Message)
    assert t2.name == 'b'
    
def test_parse_terminator_at_end_is_ignored():
    t = parse(space, 'a ; b ;')

    assert isinstance(t, W_Message)
    assert t.name == 'a'
    t1 = t.next

    assert isinstance(t1, W_Message)
    assert t1.name == ';'    
    t2 = t1.next

    assert isinstance(t2, W_Message)
    assert t2.name == 'b'
    
    assert t2.next is None