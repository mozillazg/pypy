from pypy.rlib.parsing.regexparse import parse_regex
from pypy.rlib.parsing.lexer import Lexer, Token, SourcePos

# taken from rlib/parsing/test/python_lexer.py
# reg exp helper methods
def group(*choices):
    return '(' + '|'.join(choices) + ')'
def any(*choices):
    return group(*choices) + '*'
def maybe(*choices):
    return group(*choices) + '?'

# io token definitions 
# Identifiers
Names = r'[a-zA-Z_][a-zA-Z0-9_]*'
Operators = r'(\:|\.|\'|\~|!|@|\$|%|\^|&|\*|\-|\+|/|=|\||\\|\<|\>|\?)+'
Identifiers = group(Names, Operators)

# Numbers
Decnumber = r'[1-9][0-9]*'
Exponent = r'[eE][\-\+]?[0-9]+'
Pointfloat = group(r'[0-9]+\.[0-9]*', r'\.[0-9]+') + maybe(Exponent)
Expfloat = r'[0-9]+' + Exponent
Floatnumber = group(Pointfloat, Expfloat)
Number = group(Floatnumber, Decnumber)

# Hexnuber
Hexnumber = r'0[xX][0-9a-fA-F]*'

# Comments and Whitespace, the ignored stuff
Whitespace = r'[ \f\t\n]*'
slashStarComment = r'/\*[^*/]*\*/'
slashSlashComment = r'//[^\n]*\n'
poundComment = r'#[^\n]*\n'
Comment = group(slashStarComment, slashSlashComment, poundComment)

# Parenthesis
OpenParen = group('\(', '\[', '\{')
CloseParen = group('\)', '\]', '\}')

# Qouting for strings
TriQuote = r'"""[^\"\"\"]*"""'
MonoQuote = r'"([^"]|(\\"))*"'

# ;
Terminator = r'(;'+maybe(Whitespace)+')+'



rexs = [Identifiers, Whitespace, Number, Hexnumber, Terminator, OpenParen, CloseParen, MonoQuote, TriQuote, Comment]
names = ["Identifier", "Whitespace", "Number", "HexNumber", "Terminator",
         "OpenParen", "CloseParen", "MonoQuote", "TriQuote", "Comment"]
ignores = ['Whitespace', 'Comment']


def get_lexer():
    return IoLexer()
    
class IoLexer(object):
    def __init__(self):
        super(IoLexer, self).__init__()
        self.lexer = Lexer([parse_regex(r) for r in rexs], names, ignores)
    
    def tokenize(self, input):
        tokens = self.lexer.tokenize(input)
        self._magic_tokenize(tokens)
        return tokens
    
    def _magic_tokenize(self, tokens):
        i = -1
        while(i < len(tokens)-1):
            i += 1
            if tokens[i].name != 'OpenParen':
                continue
            if tokens[i].source == '(' and (i == 0 or tokens[i-1].name != 'Identifier'):
                token_to_add = ''
            elif tokens[i].source == '[':
                token_to_add = 'squareBrackets'
            elif tokens[i].source == '{':
                token_to_add = 'curlyBrackets'
            else:
                continue
                
            tokens.insert(i, Token('Identifier', token_to_add,
                            SourcePos(tokens[i].source_pos.i,
                             tokens[i].source_pos.lineno,
                              tokens[i].source_pos.columnno)))
            i += 1
            
        return tokens