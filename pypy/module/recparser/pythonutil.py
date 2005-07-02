__all__ = ["python_parse", "pypy_parse","ast_single_input", "ast_file_input",
           "ast_eval_input" ]

import grammar
import pythonparse
from compiler.transformer import Transformer
from tuplebuilder import TupleBuilder

PYTHON_PARSER = pythonparse.PYTHON_PARSER

def python_parse(filename):
    """parse <filename> using CPython's parser module and return nested tuples
    """
    pyf = file(filename)
    import parser
    tp2 = parser.suite(pyf.read())
    return tp2.totuple()

import symbol
def pypy_parse(filename):
    """parse <filename> using PyPy's parser module and return
    a tuple of three elements :
     - The encoding declaration symbol or None if there were no encoding
       statement
     - The TupleBuilder's stack top element (instance of
       tuplebuilder.StackElement which is a wrapper of some nested tuples
       like those returned by the CPython's parser)
     - The encoding string or None if there were no encoding statement
    nested tuples
    """
    pyf = file(filename)
    text = pyf.read()
    pyf.close()
    builder = TupleBuilder(PYTHON_PARSER.rules, lineno=False)
    # make the annotator life easier
    strings = [line+'\n' for line in text.split('\n')]
    pythonparse.parse_python_source(strings, PYTHON_PARSER, 'file_input', builder)
    nested_tuples = builder.stack[-1]
    if builder.source_encoding is not None:
        return (symbol.encoding_decl, nested_tuples, builder.source_encoding)
    else:
        return (None, nested_tuples, None)

def annotateme(strings):
    builder = TupleBuilder(PYTHON_PARSER.rules, lineno=False)
    pythonparse.parse_python_source(strings, PYTHON_PARSER, 'file_input', builder)
    nested_tuples = builder.stack[-1]
    if builder.source_encoding is not None:
        return (symbol.encoding_decl, nested_tuples, builder.source_encoding)
    else:
        return (None, nested_tuples, None)

def ast_single_input( text ):
    builder = TupleBuilder( PYTHON_PARSER.rules )
    pythonparse.parse_python_source( text, PYTHON_PARSER, "single_input", builder )
    tree = builder.stack[-1]
    trans = Transformer()
    ast = trans.transform( tree )
    return ast

def ast_file_input( filename ):
    pyf = file(filename,"r")
    text = pyf.read()
    return ast_srcfile_input( text, filename )

def ast_srcfile_input( srctext, filename ):
    # TODO do something with the filename
    builder = TupleBuilder( PYTHON_PARSER.rules )
    pythonparse.parse_python_source( srctext, PYTHON_PARSER, "file_input", builder )
    tree = builder.stack[-1]
    trans = Transformer()
    ast = trans.transform( tree )
    return ast

def ast_eval_input( textsrc ):
    builder = TupleBuilder( PYTHON_PARSER.rules )
    pythonparse.parse_python_source( textsrc, PYTHON_PARSER, "eval_input", builder )
    tree = builder.stack[-1]
    trans = Transformer()
    ast = trans.transform( tree )
    return ast



if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print "python parse.py [-d N] test_file.py"
        sys.exit(1)
    if sys.argv[1] == "-d":
        debug_level = int(sys.argv[2])
        test_file = sys.argv[3]
    else:
        test_file = sys.argv[1]
    print "-"*20
    print
    print "pyparse \n", pypy_parse(test_file)
    print "parser  \n", python_parse(test_file)
