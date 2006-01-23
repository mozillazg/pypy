#!/usr/bin/env python
from grammar import BaseGrammarBuilder, Alternative, Sequence, Token
from grammar import GrammarProxy, KleeneStar, GrammarElement, build_first_sets
from grammar import EmptyToken, AbstractBuilder, AbstractContext
from ebnflexer import GrammarSource
import ebnfgrammar
from ebnfgrammar import GRAMMAR_GRAMMAR, sym_map
from syntaxtree import AbstractSyntaxVisitor
import pytoken
import pysymbol


ORDA = ord("A")
ORDZ = ord("Z")
ORDa = ord("a")
ORDz = ord("z")
ORD0 = ord("0")
ORD9 = ord("9")
ORD_ = ord("_")

def is_py_name( name ):
    if len(name)<1:
        return False
    v = ord(name[0])
    if not (ORDA <= v <= ORDZ or
            ORDa <= v <= ORDz or v == ORD_ ):
        return False
    for c in name:
        v = ord(c)
        if not (ORDA <= v <= ORDZ or 
                ORDa <= v <= ORDz or
                ORD0 <= v <= ORD9 or
                v == ORD_ ):
            return False
    return True
        
            

punct=['>=', '<>', '!=', '<', '>', '<=', '==', '\\*=',
       '//=', '%=', '^=', '<<=', '\\*\\*=', '\\', '=',
       '\\+=', '>>=', '=', '&=', '/=', '-=', '\n,', '^',
       '>>', '&', '\\+', '\\*', '-', '/', '\\.', '\\*\\*',
       '%', '<<', '//', '\\', '', '\n\\)', '\\(', ';', ':',
       '@', '\\[', '\\]', '`', '\\{', '\\}']




TERMINALS = [
    'NAME', 'NUMBER', 'STRING', 'NEWLINE', 'ENDMARKER',
    'INDENT', 'DEDENT' ]


## Grammar Visitors ##################################################
# FIXME: parsertools.py ? parser/__init__.py ?

class NameToken(Token):
    """A token that is not a keyword"""
    def __init__(self, keywords=None ):
        Token.__init__(self, pytoken.NAME)
        self.keywords = keywords

    def match(self, source, builder, level=0):
        """Matches a token.
        the default implementation is to match any token whose type
        corresponds to the object's name. You can extend Token
        to match anything returned from the lexer. for exemple
        type, value = source.next()
        if type=="integer" and int(value)>=0:
            # found
        else:
            # error unknown or negative integer
        """
        ctx = source.context()
        tk = source.next()
        if tk.codename == self.codename:
            if tk.value not in self.keywords:
                ret = builder.token( tk.codename, tk.value, source )
                return self.debug_return( ret, tk.codename, tk.value )
        source.restore( ctx )
        return 0
        
    def match_token(self, other):
        """special case of match token for tokens which are really keywords
        """
        if not isinstance(other, Token):
            raise RuntimeError("Unexpected token type")
        if other is EmptyToken:
            return False
        if other.codename != self.codename:
            return False
        if other.value in self.keywords:
            return False
        return True



def ebnf_handle_grammar(self, node):
    for rule in node.nodes:
	rule.visit(self)
    # the rules are registered already
    # we do a pass through the variables to detect
    # terminal symbols from non terminals
    for r in self.items:
        for i in range(len(r.args)):
            a = r.args[i]
	    if a.codename in self.rules:
		assert isinstance(a,Token)
		r.args[i] = self.rules[a.codename]
		if a.codename in self.terminals:
		    del self.terminals[a.codename]
    # XXX .keywords also contains punctuations
    self.terminals['NAME'].keywords = self.keywords

def ebnf_handle_rule(self, node):
    symdef = node.nodes[0].value
    self.current_rule = symdef
    self.current_subrule = 0
    alt = node.nodes[1]
    rule = alt.visit(self)
    if not isinstance(rule, Token):
	rule.codename = self.symbols.add_symbol( symdef )
    self.rules[rule.codename] = rule

def ebnf_handle_alternative(self, node):
    items = [node.nodes[0].visit(self)]
    items += node.nodes[1].visit(self)        
    if len(items) == 1 and not items[0].is_root():
	return items[0]
    alt = Alternative(self.new_symbol(), items)
    return self.new_item(alt)

def ebnf_handle_sequence( self, node ):
    """ """
    items = []
    for n in node.nodes:
	items.append( n.visit(self) )
    if len(items)==1:
	return items[0]
    elif len(items)>1:
	return self.new_item( Sequence( self.new_symbol(), items) )
    raise RuntimeError("Found empty sequence")

def ebnf_handle_sequence_cont( self, node ):
    """Returns a list of sequences (possibly empty)"""
    return [n.visit(self) for n in node.nodes]

def ebnf_handle_seq_cont_list(self, node):
    return node.nodes[1].visit(self)


def ebnf_handle_symbol(self, node):
    star_opt = node.nodes[1]
    sym = node.nodes[0].value
    terminal = self.terminals.get( sym, None )
    if not terminal:
	tokencode = pytoken.tok_values.get( sym, None )
	if tokencode is None:
	    tokencode = self.symbols.add_symbol( sym )
	    terminal = Token( tokencode )
	else:
	    terminal = Token( tokencode )
	    self.terminals[sym] = terminal

    return self.repeat( star_opt, terminal )

def ebnf_handle_option( self, node ):
    rule = node.nodes[1].visit(self)
    return self.new_item( KleeneStar( self.new_symbol(), 0, 1, rule ) )

def ebnf_handle_group( self, node ):
    rule = node.nodes[1].visit(self)
    return self.repeat( node.nodes[3], rule )

def ebnf_handle_TOK_STRING( self, node ):
    value = node.value
    tokencode = pytoken.tok_punct.get( value, None )
    if tokencode is None:
	if not is_py_name( value ):
	    raise RuntimeError("Unknown STRING value ('%s')" % value )
	# assume a keyword
	tok = Token( pytoken.NAME, value )
	if value not in self.keywords:
	    self.keywords.append( value )
    else:
	# punctuation
	tok = Token( tokencode )
    return tok

def ebnf_handle_sequence_alt( self, node ):
    res = node.nodes[0].visit(self)
    assert isinstance( res, GrammarElement )
    return res

# This will setup a mapping between
# ebnf_handle_xxx functions and ebnfgrammar.xxx
ebnf_handles = {}
for name, value in globals().items():
    if name.startswith("ebnf_handle_"):
	name = name[12:]
	key = getattr(ebnfgrammar, name )
	ebnf_handles[key] = value

def handle_unknown( self, node ):
    raise RuntimeError("Unknown Visitor for %r" % node.name)
    


class EBNFBuilder(AbstractBuilder):
    """Build a grammar tree"""
    def __init__(self, rules=None, debug=0, symbols=None ):
        if symbols is None:
            symbols = pysymbol.SymbolMapper()
        AbstractBuilder.__init__(self, rules, debug, symbols)
        self.rule_stack = []
        self.root_rules = {}
        self.keywords = []
        self.seqcounts = [] # number of items in the current sequence
        self.altcounts = [] # number of sequence in the current alternative
        self.curaltcount = 0
        self.curseqcount = 0
        self.current_subrule = 0
        self.current_rule = -1

    def new_symbol(self):
        current_rule_name = self.symbols.sym_name.get(self.current_rule,"x")
        rule_name = ":" + current_rule_name + "_%d" % self.current_subrule
        self.current_subrule += 1
        symval = self.symbols.add_anon_symbol( rule_name )
        return symval

    def get_symbolcode(self, name ):
        codename = self.symbols.sym_values.get( name, -1 )
        if codename == -1:
            codename = self.symbols.add_symbol( name )
        return codename

    def get_rule( self, name ):
        codename = self.get_symbolcode( name )
        if codename in self.root_rules:
            return self.root_rules[codename]
        proxy = GrammarProxy( codename )
        self.root_rules[codename] = proxy
        return proxy

    def context(self):
        """Return an opaque context object"""
        return None

    def restore(self, ctx):
        """Accept an opaque context object"""
        assert False, "Not supported"
    
    def alternative(self, rule, source):
#        print " alternative", rule.display(level=0,symbols=ebnfgrammar.sym_map)
        return True
    
    def pop_rules( self, count ):
        offset = len(self.rule_stack)-count
        assert offset>=0
        rules = self.rule_stack[offset:]
        del self.rule_stack[offset:]
        return rules

    def sequence(self, rule, source, elts_number):
#        print "  sequence", rule.display(level=0,symbols=ebnfgrammar.sym_map)
        _rule = rule.codename
        if _rule == ebnfgrammar.sequence:
#            print "  -sequence", self.curaltcount, self.curseqcount
            if self.curseqcount==1:
                self.curseqcount = 0
                self.curaltcount += 1
                return True
            rules = self.pop_rules(self.curseqcount)
            new_rule = Sequence( self.new_symbol(), rules )
            self.rule_stack.append( new_rule )
            self.curseqcount = 0
            self.curaltcount += 1
        elif _rule == ebnfgrammar.alternative:
#            print "  -alternative", self.curaltcount, self.curseqcount
            if self.curaltcount == 1:
                self.curaltcount = 0
                return True
            rules = self.pop_rules(self.curaltcount)
            new_rule = Alternative( self.new_symbol(), rules )
            self.rule_stack.append( new_rule )
            self.curaltcount = 0
        elif _rule == ebnfgrammar.group:
#            print "  -group", self.curaltcount, self.curseqcount
            self.curseqcount += 1
        elif _rule == ebnfgrammar.option:
#            print "  -option", self.curaltcount, self.curseqcount
            self.curseqcount += 1
        elif _rule == ebnfgrammar.rule:
#            print "  -rule", self.curaltcount, self.curseqcount
            assert len(self.rule_stack)==1
            old_rule = self.rule_stack[0]
            del self.rule_stack[0]
            old_rule.codename = self.current_rule
            self.root_rules[self.current_rule] = old_rule
            self.current_subrule = 0
        return True
    
    def token(self, name, value, source):
#        print "token", name, value
        if name == ebnfgrammar.TOK_STRING:
            self.handle_TOK_STRING( name, value )
            self.curseqcount += 1
        elif name == ebnfgrammar.TOK_SYMDEF:
            self.current_rule = self.get_symbolcode( value )
        elif name == ebnfgrammar.TOK_SYMBOL:
            rule = self.get_rule( value )
            self.rule_stack.append( rule )
            self.curseqcount += 1
        elif name == ebnfgrammar.TOK_STAR:
            top = self.rule_stack[-1]
            rule = KleeneStar( self.new_symbol(), _min=0, rule=top)
            self.rule_stack[-1] = rule
        elif name == ebnfgrammar.TOK_ADD:
            top = self.rule_stack[-1]
            rule = KleeneStar( self.new_symbol(), _min=1, rule=top)
            self.rule_stack[-1] = rule
        elif name == ebnfgrammar.TOK_BAR:
            assert self.curseqcount == 0
        elif name == ebnfgrammar.TOK_LPAR:
            self.altcounts.append( self.curaltcount )
            self.seqcounts.append( self.curseqcount )
            self.curseqcount = 0
            self.curaltcount = 0
        elif name == ebnfgrammar.TOK_RPAR:
            assert self.curaltcount == 0
            self.curaltcount = self.altcounts.pop()
            self.curseqcount = self.seqcounts.pop()
        elif name == ebnfgrammar.TOK_LBRACKET:
            self.altcounts.append( self.curaltcount )
            self.seqcounts.append( self.curseqcount )
            self.curseqcount = 0
            self.curaltcount = 0
        elif name == ebnfgrammar.TOK_RBRACKET:
            assert self.curaltcount == 0
            assert self.curseqcount == 0
            self.curaltcount = self.altcounts.pop()
            self.curseqcount = self.seqcounts.pop()
        return True

    def handle_TOK_STRING( self, name, value ):
        try:
            tokencode = pytoken.tok_punct[value]
        except KeyError:
            if not is_py_name(value):
                raise RuntimeError("Unknown STRING value ('%s')" % value)
            # assume a keyword
            tok = Token(pytoken.NAME, value)
            if value not in self.keywords:
                self.keywords.append(value)
        else:
            # punctuation
            tok = Token(tokencode, None)
        self.rule_stack.append(tok)


class EBNFVisitor(AbstractSyntaxVisitor):
    
    def __init__(self):
        self.rules = {}
        self.terminals = {}
        self.current_rule = None
        self.current_subrule = 0
        self.keywords = []
        self.items = []
        self.terminals['NAME'] = NameToken()
        self.symbols = pysymbol.SymbolMapper( pysymbol._cpython_symbols.sym_name )

    def new_symbol(self):
        current_rule_name = self.symbols.sym_name.get(self.current_rule,"x")
        rule_name = ":" + self.current_rule + "_" + str(self.current_subrule)
        self.current_subrule += 1
        symval = self.symbols.add_anon_symbol( rule_name )
        return symval

    def new_item(self, itm):
        self.items.append(itm)
        return itm

    def visit_syntaxnode( self, node ):
	visit_func = ebnf_handles.get( node.name, handle_unknown )
	return visit_func( self, node )

    def visit_tokennode( self, node ):
        return self.visit_syntaxnode( node )

    def visit_tempsyntaxnode( self, node ):
        return self.visit_syntaxnode( node )


    def repeat( self, star_opt, myrule ):
        assert isinstance( myrule, GrammarElement )
        if star_opt.nodes:
            rule_name = self.new_symbol()
            tok = star_opt.nodes[0].nodes[0]
            if tok.value == '+':
                item = KleeneStar(rule_name, _min=1, rule=myrule)
                return self.new_item(item)
            elif tok.value == '*':
                item = KleeneStar(rule_name, _min=0, rule=myrule)
                return self.new_item(item)
            else:
                raise RuntimeError("Got symbol star_opt with value='%s'"
                                  % tok.value)
        return myrule



def parse_grammar(stream):
    """parses the grammar file

    stream : file-like object representing the grammar to parse
    """
    source = GrammarSource(stream.read())
    builder = BaseGrammarBuilder()
    result = GRAMMAR_GRAMMAR.match(source, builder)
    node = builder.stack[-1]
    vis = EBNFVisitor()
    node.visit(vis)
    return vis


def parse_grammar_text(txt):
    """parses a grammar input

    stream : file-like object representing the grammar to parse
    """
    source = GrammarSource(txt)
    builder = EBNFBuilder(pysymbol._cpython_symbols)
    result = GRAMMAR_GRAMMAR.match(source, builder)
    return builder

def target_parse_grammar_text(txt):
    vis = parse_grammar_text(txt)
    # do nothing
    return None

def main_build():
    from pprint import pprint    
    grambuild = parse_grammar(file('data/Grammar2.3'))
    for i,r in enumerate(grambuild.items):
        print "%  3d : %s" % (i, r)
    pprint(grambuild.terminals.keys())
    pprint(grambuild.tokens)
    print "|".join(grambuild.tokens.keys() )

def main_build():
    import sys
    return parse_grammar_text( file(sys.argv[-1]).read() )

if __name__ == "__main__":
    result = main_build()
