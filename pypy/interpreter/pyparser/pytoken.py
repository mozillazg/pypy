# A replacement for the token module
#
# adds a new map token_values to avoid doing getattr on the module
# from PyPy RPython

N_TOKENS = 0

# This is used to replace None
NULLTOKEN = -1

# tok_rpunct = {}

def setup_tokens(parser):
    # global tok_rpunct
# For compatibility, this produces the same constant values as Python 2.4.
    parser.add_token( 'ENDMARKER' )
    parser.add_token( 'NAME' )
    parser.add_token( 'NUMBER' )
    parser.add_token( 'STRING' )
    parser.add_token( 'NEWLINE' )
    parser.add_token( 'INDENT' )
    parser.add_token( 'DEDENT' )
    parser.add_token( 'LPAR',            "(" )
    parser.add_token( 'RPAR',            ")" )
    parser.add_token( 'LSQB',            "[" )
    parser.add_token( 'RSQB',            "]" )
    parser.add_token( 'COLON',           ":" )
    parser.add_token( 'COMMA',           "," )
    parser.add_token( 'SEMI',            ";" )
    parser.add_token( 'PLUS',            "+" )
    parser.add_token( 'MINUS',           "-" )
    parser.add_token( 'STAR',            "*" )
    parser.add_token( 'SLASH',           "/" )
    parser.add_token( 'VBAR',            "|" )
    parser.add_token( 'AMPER',           "&" )
    parser.add_token( 'LESS',            "<" )
    parser.add_token( 'GREATER',         ">" )
    parser.add_token( 'EQUAL',           "=" )
    parser.add_token( 'DOT',             "." )
    parser.add_token( 'PERCENT',         "%" )
    parser.add_token( 'BACKQUOTE',       "`" )
    parser.add_token( 'LBRACE',          "{" )
    parser.add_token( 'RBRACE',          "}" )
    parser.add_token( 'EQEQUAL',         "==" )
    ne = parser.add_token( 'NOTEQUAL',   "!=" )
    parser.tok_values["<>"] = ne
    parser.add_token( 'LESSEQUAL',       "<=" )
    parser.add_token( 'GREATEREQUAL',    ">=" )
    parser.add_token( 'TILDE',           "~" )
    parser.add_token( 'CIRCUMFLEX',      "^" )
    parser.add_token( 'LEFTSHIFT',       "<<" )
    parser.add_token( 'RIGHTSHIFT',      ">>" )
    parser.add_token( 'DOUBLESTAR',      "**" )
    parser.add_token( 'PLUSEQUAL',       "+=" )
    parser.add_token( 'MINEQUAL',        "-=" )
    parser.add_token( 'STAREQUAL',       "*=" )
    parser.add_token( 'SLASHEQUAL',      "/=" )
    parser.add_token( 'PERCENTEQUAL',    "%=" )
    parser.add_token( 'AMPEREQUAL',      "&=" )
    parser.add_token( 'VBAREQUAL',       "|=" )
    parser.add_token( 'CIRCUMFLEXEQUAL', "^=" )
    parser.add_token( 'LEFTSHIFTEQUAL',  "<<=" )
    parser.add_token( 'RIGHTSHIFTEQUAL', ">>=" )
    parser.add_token( 'DOUBLESTAREQUAL', "**=" )
    parser.add_token( 'DOUBLESLASH',     "//" )
    parser.add_token( 'DOUBLESLASHEQUAL',"//=" )
    parser.add_token( 'AT',              "@" )
    parser.add_token( 'OP' )
    parser.add_token( 'ERRORTOKEN' )

# extra PyPy-specific tokens
    parser.add_token( "COMMENT" )
    parser.add_token( "NL" )

python_tokens = {}
python_opmap = {}

def _add_tok(name, *values):
    index = len(python_tokens)
    assert index < 256
    python_tokens[name] = index
    for value in values:
        python_opmap[value] = index

_add_tok('ENDMARKER')
_add_tok('NAME')
_add_tok('NUMBER')
_add_tok('STRING')
_add_tok('NEWLINE')
_add_tok('INDENT')
_add_tok('DEDENT')
_add_tok('LPAR', "(")
_add_tok('RPAR', ")")
_add_tok('LSQB', "[")
_add_tok('RSQB', "]")
_add_tok('COLON', ":")
_add_tok('COMMA',  "," )
_add_tok('SEMI', ";" )
_add_tok('PLUS', "+" )
_add_tok('MINUS', "-" )
_add_tok('STAR', "*" )
_add_tok('SLASH', "/" )
_add_tok('VBAR', "|" )
_add_tok('AMPER', "&" )
_add_tok('LESS', "<" )
_add_tok('GREATER', ">" )
_add_tok('EQUAL', "=" )
_add_tok('DOT', "." )
_add_tok('PERCENT', "%" )
_add_tok('BACKQUOTE', "`" )
_add_tok('LBRACE', "{" )
_add_tok('RBRACE', "}" )
_add_tok('EQEQUAL', "==" )
_add_tok('NOTEQUAL', "!=", "<>" )
_add_tok('LESSEQUAL', "<=" )
_add_tok('GREATEREQUAL', ">=" )
_add_tok('TILDE', "~" )
_add_tok('CIRCUMFLEX', "^" )
_add_tok('LEFTSHIFT', "<<" )
_add_tok('RIGHTSHIFT', ">>" )
_add_tok('DOUBLESTAR', "**" )
_add_tok('PLUSEQUAL', "+=" )
_add_tok('MINEQUAL', "-=" )
_add_tok('STAREQUAL', "*=" )
_add_tok('SLASHEQUAL', "/=" )
_add_tok('PERCENTEQUAL', "%=" )
_add_tok('AMPEREQUAL', "&=" )
_add_tok('VBAREQUAL', "|=" )
_add_tok('CIRCUMFLEXEQUAL', "^=" )
_add_tok('LEFTSHIFTEQUAL', "<<=" )
_add_tok('RIGHTSHIFTEQUAL', ">>=" )
_add_tok('DOUBLESTAREQUAL', "**=" )
_add_tok('DOUBLESLASH', "//" )
_add_tok('DOUBLESLASHEQUAL',"//=" )
_add_tok('AT', "@" )
_add_tok('OP')
_add_tok('ERRORTOKEN')

# extra PyPy-specific tokens
_add_tok("COMMENT")
_add_tok("NL")

del _add_tok
