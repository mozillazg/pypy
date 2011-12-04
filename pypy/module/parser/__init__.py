from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):
     """The builtin parser module."""

     applevel_name = '__builtin_parser'

     appleveldefs = {
         }

     interpleveldefs = {
         'suite'        : 'pyparser.suite',
         'expr'         : 'pyparser.expr',
         'issuite'      : 'pyparser.issuite',
         'isexpr'       : 'pyparser.isexpr',
         'STType'       : 'pyparser.STType',
         'ast2tuple'    : 'pyparser.st2tuple',
         'st2tuple'     : 'pyparser.st2tuple',
         'ast2list'     : 'pyparser.st2list',
         'ast2tuple'    : 'pyparser.st2tuple',
         'ASTType'      : 'pyparser.STType',
         'compilest'    : 'pyparser.compilest',
         'compileast'   : 'pyparser.compilest',
         'ParserError'  : 'space.new_exception_class("parser.ParserError")',
         }
