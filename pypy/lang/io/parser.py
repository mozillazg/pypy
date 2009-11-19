# TODO:
# set line and character number on messages
# operator shuffling

from pypy.rlib.parsing.regexparse import parse_regex
from pypy.rlib.parsing.lexer import Lexer, Token, SourcePos
from pypy.lang.io.model import W_Message, parse_literal, parse_hex

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
Whitespace = r'[ \f\t]*'
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
Terminator = r'([\n;]'+maybe(Whitespace)+')+'

# ,
Comma = r'\,'


rexs = [Identifiers, Whitespace, Number, Hexnumber, Terminator, OpenParen, CloseParen, MonoQuote, TriQuote, Comment, Comma]
names = ["Identifier", "Whitespace", "Number", "HexNumber", "Terminator",
         "OpenParen", "CloseParen", "MonoQuote", "TriQuote", "Comment", "Comma"]
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
            if tokens[i].name == 'Terminator':
                tokens[i].source = ';'
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
        
def parse(space, string):
    return IoParser(string, space).parse()
    
class IoParser(object):
    def __init__(self, code, space):
        super(IoParser, self).__init__()
        self.code = code
        self.space = space
        self.tokens = get_lexer().tokenize(self.code)
        if len(self.tokens) > 0 and self.tokens[0].name == 'Terminator':
            self.tokens.pop(0)
        if len(self.tokens) > 0 and  self.tokens[-1].name == 'Terminator':
            self.tokens.pop()
        

    def parse(self):
        if len(self.tokens) == 0:
            return W_Message(self.space, 'nil', [])
        token = self.tokens.pop(0)
        # method = getattr(self, "parse_" + token.name.lower())
        arguments = self.parse_arguments()
        message = self.parse_token(token, arguments)
        message.next = self.parse_next()
        return message
        
    def parse_next(self):
        if len(self.tokens) > 0 and self.tokens[0].name not in ['Comma', 'OpenParen', 'CloseParen']:
            return self.parse()
        else:
            return None
            
    def parse_arguments(self):
        if len(self.tokens) > 0 and self.tokens[0].name == 'OpenParen':
            arguments = []
            t = self.tokens.pop(0)
            assert t.name == 'OpenParen'
        
            while self.tokens[0].name != 'CloseParen':
                if self.tokens[0].name == 'Comma':
                    self.tokens.pop(0)
                arguments.append(self.parse())
        
            t = self.tokens.pop(0)
            assert t.name == 'CloseParen'
        else:
            arguments = []
        return arguments
        
    def parse_token(self, token, args=[]):
        m = W_Message(self.space, token.source, args)
        if token.name != 'Identifier':
            m.cached_result = parse_literal(self.space, token.source)
        return m
