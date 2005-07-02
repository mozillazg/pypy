#!/usr/bin/env python
from pythonlexer import Source
from ebnfparse import parse_grammar
import sys
import os
import symbol
import grammar

# parse the python grammar corresponding to our CPython version
_ver = ".".join([str(i) for i in sys.version_info[:2]])
PYTHON_GRAMMAR = os.path.join( os.path.dirname(__file__), "data", "Grammar" + _ver )

def python_grammar():
    """returns a """
    level = grammar.DEBUG
    grammar.DEBUG = 0
    gram = parse_grammar( file(PYTHON_GRAMMAR) )
    grammar.DEBUG = level
    # Build first sets for each rule (including anonymous ones)
    grammar.build_first_sets(gram.items)
    return gram

PYTHON_PARSER = python_grammar()


def parse_python_source( textsrc, gram, goal, builder=None ):
    """Parse a python source according to goal"""
    target = gram.rules[goal]
    src = Source(textsrc)
    if builder is None:
        builder = grammar.BaseGrammarBuilder(debug=False, rules=gram.rules)
    result = target.match(src, builder)
    # <HACK> XXX find a clean way to process encoding declarations
    builder.source_encoding = src.encoding
    # </HACK>
    if not result:
        return None
    # raise SyntaxError("at %s" % src.debug() )
    return builder

def parse_file_input(pyf, gram, builder=None):
    """Parse a python file"""
    return parse_python_source( pyf.read(), gram, "file_input", builder )
    
def parse_single_input(textsrc, gram, builder=None):
    """Parse a python single statement"""
    return parse_python_source( textsrc, gram, "single_input", builder )

def parse_eval_input(textsrc, gram, builder=None):
    """Parse a python expression"""
    return parse_python_source( textsrc, gram, "eval_input", builder )
