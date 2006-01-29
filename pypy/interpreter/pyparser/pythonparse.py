#!/usr/bin/env python
"""This module loads the python Grammar (2.3 or 2.4) and builds
the parser for this grammar in the global PYTHON_PARSER

helper functions are provided that use the grammar to parse
using file_input, single_input and eval_input targets
"""
import sys
import os
from pypy.interpreter.error import OperationError, debug_print
from pypy.interpreter import gateway
from pypy.interpreter.pyparser.error import SyntaxError
from pypy.tool.option import Options
from pypy.interpreter.pyparser.pythonlexer import Source, match_encoding_declaration
import pypy.interpreter.pyparser.pysymbol as pysymbol
import pypy.interpreter.pyparser.pytoken as pytoken
import pypy.interpreter.pyparser.ebnfparse as ebnfparse
import pypy.interpreter.pyparser.grammar as grammar

try:
    from pypy.interpreter.pyparser import symbol
except ImportError:
    # for standalone testing
    import symbol

from codeop import PyCF_DONT_IMPLY_DEDENT

class PythonParser(grammar.Parser):
    """Wrapper class for python grammar"""
    def __init__(self):
        grammar.Parser.__init__(self)

    def parse_source(self, textsrc, goal, builder, flags=0):
        """Parse a python source according to goal"""
        # Detect source encoding.
        if textsrc[:3] == '\xEF\xBB\xBF':
            textsrc = textsrc[3:]
            enc = 'utf-8'
        else:
            enc = _normalize_encoding(_check_for_encoding(textsrc))
            if enc is not None and enc not in ('utf-8', 'iso-8859-1'):
                textsrc = recode_to_utf8(builder.space, textsrc, enc)

        lines = [line + '\n' for line in textsrc.split('\n')]
        builder.source_encoding = enc
        if len(textsrc) and textsrc[-1] == '\n':
            lines.pop()
            flags &= ~PyCF_DONT_IMPLY_DEDENT
        return self.parse_lines(lines, goal, builder, flags)

    def parse_lines(self, lines, goal, builder, flags=0):
        goalnumber = self.symbols[goal]
        target = self.root_rules[goalnumber]
        src = Source(self, lines, flags)

        result = target.match(src, builder)
        if not result:
            line, lineno = src.debug()
            # XXX needs better error messages
            raise SyntaxError("invalid syntax", lineno, -1, line)
            # return None
        return builder

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
    return match_encoding_declaration(line[i:])

PYTHON_VERSION = ".".join([str(i) for i in sys.version_info[:2]])
def get_grammar_file( version ):
    """returns the python grammar corresponding to our CPython version"""
    if version == "native":
        _ver = PYTHON_VERSION
    elif version in ("2.3","2.4"):
        _ver = version
    return os.path.join( os.path.dirname(__file__), "data", "Grammar" + _ver ), _ver

# unfortunately the command line options are not parsed yet
PYTHON_GRAMMAR, PYPY_VERSION = get_grammar_file( Options.version )


def load_python_grammar(fname):
    """Loads the grammar using the 'dynamic' rpython parser"""
    _grammar_file = file(fname)
    parser = PYTHON_PARSER
    # populate symbols
    ebnfparse.parse_grammar_text( parser, file(fname).read() )
    return parser

def reload_grammar(version):
    """helper function to test with pypy different grammars"""
    global PYTHON_GRAMMAR, PYTHON_PARSER, PYPY_VERSION
    PYTHON_GRAMMAR, PYPY_VERSION = get_grammar_file( version )
    debug_print( "Reloading grammar %s" % PYTHON_GRAMMAR )
    PYTHON_PARSER = python_grammar( PYTHON_GRAMMAR )

def parse_file_input(pyf, gram, builder ):
    """Parse a python file"""
    return gram.parse_source( pyf.read(), "file_input", builder )

def parse_single_input(textsrc, gram, builder ):
    """Parse a python single statement"""
    return gram.parse_source( textsrc, "single_input", builder )

def parse_eval_input(textsrc, gram, builder):
    """Parse a python expression"""
    return gram.parse_source( textsrc, "eval_input", builder )

def grammar_rules( space ):
    return space.wrap( PYTHON_PARSER.root_rules )

def dot_node( gen, rule_name, rule, symbols, edges, count ):
    from pypy.interpreter.pyparser.grammar import KleeneStar, Sequence, Alternative, Token
    subrule_name = symbols.get( rule.codename, rule.codename )
    label = None
    if not subrule_name.startswith(":"+rule_name):
        node_name = rule_name + "_ext_" + str(count[0])
        count[0]+=1
        label = subrule_name
        gen.emit_node( node_name, shape="parallelogram", label=subrule_name )
        edges.append( (node_name, subrule_name) )
        return node_name
    subrule_name = subrule_name.replace(":","_")
    if isinstance(rule, KleeneStar):
        node = dot_node( gen, rule_name, rule.args[0], symbols, edges, count )
        gen.emit_edge( node, node, label=rule.get_star(), style='solid' )
        return node
    elif isinstance(rule, Sequence):
        gen.enter_subgraph( subrule_name )
        first_node = None
        for n in rule.args:
            node_name = dot_node( gen, rule_name, n, symbols, edges, count )
            if first_node:
                gen.emit_edge( first_node, node_name, style='solid' )
            first_node = node_name
        gen.leave_subgraph()
        return subrule_name
    elif isinstance(rule, Alternative):
        gen.enter_subgraph( subrule_name )
        for n in rule.args:
            node_name = dot_node( gen, rule_name, n, symbols, edges, count )
        gen.leave_subgraph()
        return subrule_name
    elif isinstance(rule, Token):
        node_name = rule_name + "_ext_" + str(count[0])
        count[0]+=1
        gen.emit_node( node_name, shape='box', label=rule.display( 0, symbols ) )
        return node_name
    raise RuntimeError("Unknown node type")

def gen_grammar_dot( name, root_rules, rules, symbols ):
    """Quick hack to output a dot graph of the grammar"""
    from pypy.translator.tool.make_dot import DotGen
    gen = DotGen(name)
    edges = []
    count = [0]
    for r in root_rules:
        rule_name = symbols.get( r.codename, r.codename )
        gen.emit_node( rule_name, shape='hexagon', label=r.display(0,symbols) )
        for rule in r.args:
            node = dot_node( gen, rule_name, rule, symbols, edges, count )
            gen.emit_edge( rule_name, node, style='solid' )
    for left, right in edges:
        gen.emit_edge( left, right, style='solid' )
    gen.generate(target='ps')


def parse_grammar(space, w_src):
    """Loads the grammar using the 'dynamic' rpython parser"""
    src = space.str_w( w_src )
    ebnfbuilder = ebnfparse.parse_grammar_text( src )
    ebnfbuilder.resolve_rules()
    grammar.build_first_sets(ebnfbuilder.all_rules)
    return space.wrap( ebnfbuilder.root_rules )

debug_print( "Loading grammar %s" % PYTHON_GRAMMAR )
PYTHON_PARSER = PythonParser()
PYTHON_PARSER.load_symbols( symbol.sym_name )
pytoken.setup_tokens( PYTHON_PARSER )
load_python_grammar( PYTHON_GRAMMAR )


if __name__=="__main__":
    symbols = {}
    symbols.update( pytoken.tok_name )
    symbols.update( pysymbol._cpython_symbols.sym_name )
    gen_grammar_dot("grammar", PYTHON_PARSER.rules.values(), PYTHON_PARSER.items, symbols )
