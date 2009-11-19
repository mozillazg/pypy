from pypy.lang.io.register import register_method
from pypy.lang.io.model import W_Object, W_Number
from pypy.lang.io.parser import get_lexer, parse
@register_method('Compiler', 'tokensForString')
def compiler_tokens_for_string(space, w_target, w_message, w_context):
    input = w_message.arguments[0].eval(space, w_context, w_target).value
    io_tokens = []
    for token in get_lexer().tokenize(input):
        t = W_Object(space)
        if token.source in ['[', '{'] and len(io_tokens) > 0:
            io_tokens[-1].slots['character'].value = token.source_pos.columnno
        t.slots['character'] = W_Number(space, len(token.source) + token.source_pos.columnno)
        t.slots['line'] = W_Number(space, token.source_pos.lineno + 1)
        t.slots['type'] = space.w_sequence.clone_and_init(token.name)
        t.slots['name'] = space.w_sequence.clone_and_init(token.source)
        io_tokens.append(t)
    
    return space.w_list.clone_and_init(space, io_tokens)
    
@register_method('Compiler', 'messageForString', unwrap_spec=[object, str])
def compiler_message_for_string(space, w_target, string):
    return parse(space, string)