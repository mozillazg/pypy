"""This is a lexer for a Python recursive descent parser
it obeys the TokenSource interface defined for the grammar
analyser in grammar.py
"""

import re
from grammar import TokenSource, Token

DEBUG = False

## Lexer for Python's grammar ########################################
g_symdef = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*:",re.M)
g_symbol = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*",re.M)
g_string = re.compile(r"'[^']+'",re.M)
g_tok = re.compile(r"\[|\]|\(|\)|\*|\+|\|",re.M)
g_skip = re.compile(r"\s*(#.*$)?",re.M)

class GrammarSource(TokenSource):
    """The grammar tokenizer"""
    def __init__(self, inpstring ):
        TokenSource.__init__(self)
        self.input = inpstring
        self.pos = 0
        self._peeked = None

    def context(self):
        return self.pos, self._peeked

    def offset(self, ctx=None):
        if ctx is None:
            return self.pos
        else:
            assert type(ctx)==int
            return ctx

    def restore(self, ctx):
        self.pos, self._peeked = ctx

    def next(self):
        if self._peeked is not None:
            peeked = self._peeked
            self._peeked = None
            return peeked
        
        pos = self.pos
        inp = self.input
        m = g_skip.match(inp, pos)
        while m and pos!=m.end():
            pos = m.end()
            if pos==len(inp):
                self.pos = pos
                return Token("EOF", None)
            m = g_skip.match(inp, pos)
        m = g_symdef.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return Token('SYMDEF',tk[:-1])
        m = g_tok.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return Token(tk,tk)
        m = g_string.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return Token('STRING',tk[1:-1])
        m = g_symbol.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return Token('SYMBOL',tk)
        raise ValueError("Unknown token at pos=%d context='%s'" % (pos,inp[pos:pos+20]) )

    def peek(self):
        if self._peeked is not None:
            return self._peeked
        self._peeked = self.next()
        return self._peeked

    def debug(self):
        return self.input[self.pos:self.pos+20]
