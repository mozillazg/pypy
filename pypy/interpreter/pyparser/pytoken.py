# A replacement for the token module
#
# adds a new map token_values to avoid doing getattr on the module
# from PyPy RPython

N_TOKENS = 0

# This is used to replace None
NULLTOKEN = -1

tok_name = {-1 : 'NULLTOKEN'}
tok_values = {'NULLTOKEN' : -1}

# tok_rpunct = {}

def setup_tokens(parser):
    # global tok_rpunct
# For compatibility, this produces the same constant values as Python 2.4.
    from grammar import Token
    parser.add_token(Token('ENDMARKER' ))
    parser.add_token(Token('NAME' ))
    parser.add_token(Token('NUMBER' ))
    parser.add_token(Token('STRING' ))
    parser.add_token(Token('NEWLINE' ))
    parser.add_token(Token('INDENT' ))
    parser.add_token(Token('DEDENT' ))
    parser.add_token(Token('LPAR',            "(" ))
    parser.add_token(Token('RPAR',            ")" ))
    parser.add_token(Token('LSQB',            "[" ))
    parser.add_token(Token('RSQB',            "]" ))
    parser.add_token(Token('COLON',           ":" ))
    parser.add_token(Token('COMMA',           "," ))
    parser.add_token(Token('SEMI',            ";" ))
    parser.add_token(Token('PLUS',            "+" ))
    parser.add_token(Token('MINUS',           "-" ))
    parser.add_token(Token('STAR',            "*" ))
    parser.add_token(Token('SLASH',           "/" ))
    parser.add_token(Token('VBAR',            "|" ))
    parser.add_token(Token('AMPER',           "&" ))
    parser.add_token(Token('LESS',            "<" ))
    parser.add_token(Token('GREATER',         ">" ))
    parser.add_token(Token('EQUAL',           "=" ))
    parser.add_token(Token('DOT',             "." ))
    parser.add_token(Token('PERCENT',         "%" ))
    parser.add_token(Token('BACKQUOTE',       "`" ))
    parser.add_token(Token('LBRACE',          "{" ))
    parser.add_token(Token('RBRACE',          "}" ))
    parser.add_token(Token('EQEQUAL',         "==" ))
    ne = parser.add_token(Token('NOTEQUAL',   "!=" ))
    parser.tok_values["<>"] = ne
    parser.add_token(Token('LESSEQUAL',       "<=" ))
    parser.add_token(Token('GREATEREQUAL',    ">=" ))
    parser.add_token(Token('TILDE',           "~" ))
    parser.add_token(Token('CIRCUMFLEX',      "^" ))
    parser.add_token(Token('LEFTSHIFT',       "<<" ))
    parser.add_token(Token('RIGHTSHIFT',      ">>" ))
    parser.add_token(Token('DOUBLESTAR',      "**" ))
    parser.add_token(Token('PLUSEQUAL',       "+=" ))
    parser.add_token(Token('MINEQUAL',        "-=" ))
    parser.add_token(Token('STAREQUAL',       "*=" ))
    parser.add_token(Token('SLASHEQUAL',      "/=" ))
    parser.add_token(Token('PERCENTEQUAL',    "%=" ))
    parser.add_token(Token('AMPEREQUAL',      "&=" ))
    parser.add_token(Token('VBAREQUAL',       "|=" ))
    parser.add_token(Token('CIRCUMFLEXEQUAL', "^=" ))
    parser.add_token(Token('LEFTSHIFTEQUAL',  "<<=" ))
    parser.add_token(Token('RIGHTSHIFTEQUAL', ">>=" ))
    parser.add_token(Token('DOUBLESTAREQUAL', "**=" ))
    parser.add_token(Token('DOUBLESLASH',     "//" ))
    parser.add_token(Token('DOUBLESLASHEQUAL',"//=" ))
    parser.add_token(Token('AT',              "@" ))
    parser.add_token(Token('OP' ))
    parser.add_token(Token('ERRORTOKEN' ))

# extra PyPy-specific tokens
    parser.add_token(Token("COMMENT" ))
    parser.add_token(Token("NL" ))

