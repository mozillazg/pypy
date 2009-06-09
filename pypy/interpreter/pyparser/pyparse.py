import codeop
from pypy.interpreter import gateway
from pypy.interpreter.pyparser.error import SyntaxError, IndentationError
from pypy.interpreter.pyparser import parser, pytokenizer, pygram, error


_recode_to_utf8 = gateway.applevel(r'''
    def _recode_to_utf8(text, encoding):
        return unicode(text, encoding).encode("utf-8")
''').interphook('_recode_to_utf8')

def recode_to_utf8(space, text, encoding):
    return space.str_w(_recode_to_utf8(space, space.wrap(text),
                                          space.wrap(encoding)))
def _normalize_encoding(encoding):
    """returns normalized name for <encoding>

    see dist/src/Parser/tokenizer.c 'get_normal_name()'
    for implementation details / reference

    NOTE: for now, parser.suite() raises a MemoryError when
          a bad encoding is used. (SF bug #979739)
    """
    if encoding is None:
        return None
    # lower() + '_' / '-' conversion
    encoding = encoding.replace('_', '-').lower()
    if encoding.startswith('utf-8'):
        return 'utf-8'
    for variant in ['latin-1', 'iso-latin-1', 'iso-8859-1']:
        if encoding.startswith(variant):
            return 'iso-8859-1'
    return encoding

def _check_for_encoding(s):
    eol = s.find('\n')
    if eol < 0:
        return _check_line_for_encoding(s)
    enc = _check_line_for_encoding(s[:eol])
    if enc:
        return enc
    eol2 = s.find('\n', eol + 1)
    if eol2 < 0:
        return _check_line_for_encoding(s[eol + 1:])
    return _check_line_for_encoding(s[eol + 1:eol2])


def _check_line_for_encoding(line):
    """returns the declared encoding or None"""
    i = 0
    for i in range(len(line)):
        if line[i] == '#':
            break
        if line[i] not in ' \t\014':
            return None
    return pytokenizer.match_encoding_declaration(line[i:])


_targets = {
'eval' : pygram.syms.eval_input,
'single' : pygram.syms.single_input,
'exec' : pygram.syms.file_input,
}

class PythonParser(parser.Parser):

    def parse_source(self, textsrc, mode="exec", flags=0):
        """Parse a python source according to goal"""
        # Detect source encoding.
        enc = None
        if textsrc[:3] == '\xEF\xBB\xBF':
            textsrc = textsrc[3:]
            enc = 'utf-8'
            # check that there is no explicit encoding declared
            decl_enc = _check_for_encoding(textsrc)
            if decl_enc is not None:
                raise SyntaxError("encoding declaration in Unicode string")
        else:
            enc = _normalize_encoding(_check_for_encoding(textsrc))
            if enc is not None and enc not in ('utf-8', 'iso-8859-1'):
                try:
                    textsrc = recode_to_utf8(builder.space, textsrc, enc)
                except OperationError, e:
                    # if the codec is not found, LookupError is raised.  we
                    # check using 'is_w' not to mask potential IndexError or
                    # KeyError
                    space = builder.space
                    if space.is_w(e.w_type, space.w_LookupError):
                        raise SyntaxError("Unknown encoding: %s" % enc)
                    raise

        self.prepare(_targets[mode])
        try:
            tokens = pytokenizer.generate_tokens(textsrc, flags)
            for tp, value, lineno, column, line in tokens:
                if self.add_token(tp, value, lineno, column, line):
                    break
        except parser.ParseError, e:
            new_err = error.IndentationError
            if tp == pygram.tokens.INDENT:
                msg = "unexpected indent"
            elif e.expected == pygram.tokens.INDENT:
                msg = "expected indented block"
            else:
                new_err = error.SyntaxError
                msg = "invalid syntax"
            raise new_err(msg, e.lineno, e.column, e.line)
        else:
            tree = self.root
        finally:
            self.root = None
        if enc is not None:
            # Wrap the tree in an encoding_decl node for the AST builder.
            tree = parser.Node(pygram.syms.encoding_decl, enc, [tree], 0, 0)
        return tree
