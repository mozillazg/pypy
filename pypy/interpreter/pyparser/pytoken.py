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
    parser.add_token(Token(parser, 'ENDMARKER' ))
    parser.add_token(Token(parser, 'NAME' ))
    parser.add_token(Token(parser, 'NUMBER' ))
    parser.add_token(Token(parser, 'STRING' ))
    parser.add_token(Token(parser, 'NEWLINE' ))
    parser.add_token(Token(parser, 'INDENT' ))
    parser.add_token(Token(parser, 'DEDENT' ))
    parser.add_token(Token(parser, 'LPAR',            "(" ))
    parser.add_token(Token(parser, 'RPAR',            ")" ))
    parser.add_token(Token(parser, 'LSQB',            "[" ))
    parser.add_token(Token(parser, 'RSQB',            "]" ))
    parser.add_token(Token(parser, 'COLON',           ":" ))
    parser.add_token(Token(parser, 'COMMA',           "," ))
    parser.add_token(Token(parser, 'SEMI',            ";" ))
    parser.add_token(Token(parser, 'PLUS',            "+" ))
    parser.add_token(Token(parser, 'MINUS',           "-" ))
    parser.add_token(Token(parser, 'STAR',            "*" ))
    parser.add_token(Token(parser, 'SLASH',           "/" ))
    parser.add_token(Token(parser, 'VBAR',            "|" ))
    parser.add_token(Token(parser, 'AMPER',           "&" ))
    parser.add_token(Token(parser, 'LESS',            "<" ))
    parser.add_token(Token(parser, 'GREATER',         ">" ))
    parser.add_token(Token(parser, 'EQUAL',           "=" ))
    parser.add_token(Token(parser, 'DOT',             "." ))
    parser.add_token(Token(parser, 'PERCENT',         "%" ))
    parser.add_token(Token(parser, 'BACKQUOTE',       "`" ))
    parser.add_token(Token(parser, 'LBRACE',          "{" ))
    parser.add_token(Token(parser, 'RBRACE',          "}" ))
    parser.add_token(Token(parser, 'EQEQUAL',         "==" ))
    ne = parser.add_token(Token(parser, 'NOTEQUAL',   "!=" ))
    parser.tok_values["<>"] = ne
    parser.add_token(Token(parser, 'LESSEQUAL',       "<=" ))
    parser.add_token(Token(parser, 'GREATEREQUAL',    ">=" ))
    parser.add_token(Token(parser, 'TILDE',           "~" ))
    parser.add_token(Token(parser, 'CIRCUMFLEX',      "^" ))
    parser.add_token(Token(parser, 'LEFTSHIFT',       "<<" ))
    parser.add_token(Token(parser, 'RIGHTSHIFT',      ">>" ))
    parser.add_token(Token(parser, 'DOUBLESTAR',      "**" ))
    parser.add_token(Token(parser, 'PLUSEQUAL',       "+=" ))
    parser.add_token(Token(parser, 'MINEQUAL',        "-=" ))
    parser.add_token(Token(parser, 'STAREQUAL',       "*=" ))
    parser.add_token(Token(parser, 'SLASHEQUAL',      "/=" ))
    parser.add_token(Token(parser, 'PERCENTEQUAL',    "%=" ))
    parser.add_token(Token(parser, 'AMPEREQUAL',      "&=" ))
    parser.add_token(Token(parser, 'VBAREQUAL',       "|=" ))
    parser.add_token(Token(parser, 'CIRCUMFLEXEQUAL', "^=" ))
    parser.add_token(Token(parser, 'LEFTSHIFTEQUAL',  "<<=" ))
    parser.add_token(Token(parser, 'RIGHTSHIFTEQUAL', ">>=" ))
    parser.add_token(Token(parser, 'DOUBLESTAREQUAL', "**=" ))
    parser.add_token(Token(parser, 'DOUBLESLASH',     "//" ))
    parser.add_token(Token(parser, 'DOUBLESLASHEQUAL',"//=" ))
    parser.add_token(Token(parser, 'AT',              "@" ))
    parser.add_token(Token(parser, 'OP' ))
    parser.add_token(Token(parser, 'ERRORTOKEN' ))

# extra PyPy-specific tokens
    parser.add_token(Token(parser, "COMMENT" ))
    parser.add_token(Token(parser, "NL" ))

