import py
from pypy.rlib.parsing.lexer import Lexer, Token, SourcePos

from pypy.lang.io.parser import get_lexer

iolexer = get_lexer()
def test_lex_identifier():
    inp = "Compiler"
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token("Identifier", "Compiler", SourcePos(0, 0, 0))
    
def test_lex_identifier2():
    inp = "@Compiler"
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token("Identifier", "@", SourcePos(0, 0, 0))
    assert tokens[1] == Token("Identifier", "Compiler", SourcePos(1, 0, 1))
    
def test_lex_identifier3():
    inp = "_"
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token("Identifier", "_", SourcePos(0, 0, 0))
    
    
def test_lex_identifier4():
    inp = "@@@@"
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token("Identifier", "@@@@", SourcePos(0, 0, 0))
    
def test_lex_identifier5():
    inp = ":="
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token("Identifier", ":=", SourcePos(0, 0, 0))

def test_lex_identifier6():
    inp = "::=::"
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token("Identifier", "::=::", SourcePos(0, 0, 0))
    
def test_lex_ignores_whitespace():
    inp = "Foo       bar"
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token("Identifier", "Foo", SourcePos(0, 0, 0))
    assert tokens[1] == Token("Identifier", "bar", SourcePos(10, 0, 10))
    
def test_lex_numbers():
    inp = '12345678901234567890'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('Number', '12345678901234567890', SourcePos(0, 0, 0))
    
def test_lex_numbers2():
    inp = '.239'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('Number', '.239', SourcePos(0, 0, 0))
    
def test_lex_numbers3():
    inp = '1.239'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('Number', '1.239', SourcePos(0, 0, 0))
    
def test_lex_numbers4():
    inp = '1.239e+123'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('Number', '1.239e+123', SourcePos(0, 0, 0))

def test_lex_numbers5():
    inp = '1239e+123'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('Number', '1239e+123', SourcePos(0, 0, 0))
    
def test_lex_hexnumber():
    inp = '0xCAFFEE'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('HexNumber', '0xCAFFEE', SourcePos(0, 0, 0))

def test_lex_hexnumber():
    inp = '0XCAFFEE'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('HexNumber', '0XCAFFEE', SourcePos(0, 0, 0))

def test_lex_terminator():
    inp = ';'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('Terminator', ';', SourcePos(0, 0, 0))

def test_lex_terminator1():
    inp = ';;'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('Terminator', ';', SourcePos(0, 0, 0))
    assert len(tokens) == 1
    
def test_lex_terminator2():
    inp = '; ;'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('Terminator', ';', SourcePos(0, 0, 0))
    assert len(tokens) == 1

def test_lex_newline_terminator():
    inp = '\n'
    tokens = iolexer.tokenize(inp)
    assert len(tokens) == 1
    assert tokens[0] == Token('Terminator', ';', SourcePos(0, 0, 0))
    
def test_lex_open_paren():
    inp = '()'
    tokens = iolexer.tokenize(inp)
    assert Token('OpenParen', '(', SourcePos(0, 0, 0)) in tokens
    
def test_lex_close_paren():
    inp = '()'
    tokens = iolexer.tokenize(inp)
    assert Token('CloseParen', ')', SourcePos(1, 0, 1)) in tokens
    
def test_lex_monoquote():
    inp = '"MonoQuote" "qertz"'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('MonoQuote', '"MonoQuote"', SourcePos(0, 0, 0))
    
def test_lex_monoquote_escapes():
    inp = '"a\\"a"'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('MonoQuote', '"a\\"a"', SourcePos(0, 0, 0))

def test_lex_triquote():
    inp = '"""TriQuote"""'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('TriQuote', '"""TriQuote"""', SourcePos(0, 0, 0))
    
def test_lex_pound_comment_is_ignored():
    inp = """a # foo bar
    """
    tokens = iolexer.tokenize(inp)
    assert tokens[0].name != 'Comment'
    assert len(tokens) == 1
    
def test_lex_pound_comment_is_ignored():
    inp = """a // foo bar
    """
    tokens = iolexer.tokenize(inp)
    assert tokens[0].name != 'Comment'
    assert len(tokens) == 1
    
def test_lex_slash_star_comment_is_ignored():
    inp = """a /* foo bar */ q"""
    tokens = iolexer.tokenize(inp)
    assert tokens[0].name != 'Comment'
    assert tokens[1].name != 'Comment'
    assert len(tokens) == 2
    
def test_lex_paren_adds_anon_message():
    inp = '()'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('Identifier', '', SourcePos(0, 0, 0))
    assert tokens[1] == Token('OpenParen', '(', SourcePos(0, 0, 0))
    
def test_lex_paren_adds_only_when_no_receiver():
    inp = 'foo ()'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('Identifier', 'foo', SourcePos(0, 0, 0))
    assert tokens[1] == Token('OpenParen', '(', SourcePos(4, 0, 4))

def test_lex_open_paren():
    inp = '()'
    tokens = iolexer.tokenize(inp)
    assert Token('OpenParen', '(', SourcePos(0, 0, 0)) in tokens

def test_lex_close_paren():
    inp = '()'
    tokens = iolexer.tokenize(inp)
    assert Token('CloseParen', ')', SourcePos(1, 0, 1)) in tokens


def test_lex_squareBrackets():
    inp = '[]'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('Identifier', 'squareBrackets', SourcePos(0, 0, 0))
    assert tokens[1] == Token('OpenParen', '[', SourcePos(0, 0, 0))
    assert tokens[2] == Token('CloseParen', ']', SourcePos(1, 0, 1))

def test_lex_curlyBrackets():
    inp = '{}'
    tokens = iolexer.tokenize(inp)
    assert tokens[0] == Token('Identifier', 'curlyBrackets', SourcePos(0, 0, 0))
    assert tokens[1] == Token('OpenParen', '{', SourcePos(0, 0, 0))
    assert tokens[2] == Token('CloseParen', '}', SourcePos(1, 0, 1))
    
def test_lex_comma_token():
    inp = '(1, 2)'
    tokens = iolexer.tokenize(inp)
    assert tokens[3] == Token('Comma', ',', SourcePos(2, 0, 2))