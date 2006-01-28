# This module contains the grammar parser
# and the symbol mappings

from grammar import BaseGrammarBuilder, Alternative, Sequence, Token, \
     KleeneStar, GrammarElement, Parser


## sym_map = {}
## sym_rmap = {}
## _count = 0

## def g_add_symbol( name ):
##     global _count
##     if name in sym_rmap:
##         return sym_rmap[name]
##     val = _count
##     _count += 1
##     sym_map[val] = name
##     sym_rmap[name] = val
##     globals()[name] = val
##     return val


## tok_map = {}
## tok_rmap = {}

## def g_add_token(sym, name):
##     global _count
##     if name in tok_rmap:
##         return tok_rmap[name]
##     val = _count
##     _count += 1
##     tok_map[val] = name
##     tok_rmap[name] = val
##     sym_map[val] = sym
##     sym_rmap[sym] = val
##     globals()[sym] = val
##     return val



## g_add_token('EOF', 'EOF')
class GrammarParser(Parser):
    pass

GRAMMAR_GRAMMAR = GrammarParser()


def grammar_grammar():
    """
    (mostly because of g_add_token I suppose)
    Builds the grammar for the grammar file

    Here's the description of the grammar's grammar ::

      grammar: rule+
      rule: SYMDEF alternative
      
      alternative: sequence ( '|' sequence )+
      star: '*' | '+'
      sequence: (SYMBOL star? | STRING | option | group )+
      option: '[' alternative ']'
      group: '(' alternative ')' star?
    """
    global sym_map
    p = GRAMMAR_GRAMMAR
    p.add_token('EOF','EOF')

    # star: '*' | '+'
    star          = p.Alternative_n( "star", [p.Token_n('TOK_STAR', '*'), p.Token_n('TOK_ADD', '+')] )
    star_opt      = p.KleeneStar_n( "star_opt", 0, 1, rule=star )

    # rule: SYMBOL ':' alternative
    symbol        = p.Sequence_n(    "symbol", [p.Token_n('TOK_SYMBOL'), star_opt] )
    symboldef     = p.Token_n(       'TOK_SYMDEF' )
    alternative   = p.Sequence_n(    "alternative", [])
    rule          = p.Sequence_n(    "rule", [symboldef, alternative] )

    # grammar: rule+
    grammar       = p.KleeneStar_n(  "grammar", _min=1, rule=rule )

    # alternative: sequence ( '|' sequence )*
    sequence      = p.KleeneStar_n(  "sequence", 1 )
    seq_cont_list = p.Sequence_n(    "seq_cont_list", [p.Token_n('TOK_BAR', '|'), sequence] )
    sequence_cont = p.KleeneStar_n(  "sequence_cont",0, rule=seq_cont_list )

    alternative.args = [ sequence, sequence_cont ]

    # option: '[' alternative ']'
    option        = p.Sequence_n(    "option", [p.Token_n('TOK_LBRACKET', '['), alternative, p.Token_n('TOK_RBRACKET', ']')] )

    # group: '(' alternative ')'
    group         = p.Sequence_n(    "group",  [p.Token_n('TOK_LPAR', '('), alternative, p.Token_n('TOK_RPAR', ')'), star_opt] )

    # sequence: (SYMBOL | STRING | option | group )+
    string = p.Token_n('TOK_STRING')
    alt           = p.Alternative_n( "sequence_alt", [symbol, string, option, group] )
    sequence.args = [ alt ]

    p.root_rules['grammar'] = grammar
    p.build_first_sets()
    return p


grammar_grammar()
for _sym, _value in GRAMMAR_GRAMMAR.symbols.items():
    assert not hasattr( GRAMMAR_GRAMMAR, _sym )
    setattr(GRAMMAR_GRAMMAR, _sym, _value )

for _sym, _value in GRAMMAR_GRAMMAR.tokens.items():
    assert not hasattr( GRAMMAR_GRAMMAR, _sym )
    setattr(GRAMMAR_GRAMMAR, _sym, _value )

# cleanup
## del _sym
## del _value
del grammar_grammar
## del g_add_symbol
# del g_add_token
