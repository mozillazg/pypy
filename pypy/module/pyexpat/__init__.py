import py

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    appleveldefs = {
        'ExpatError' : 'app_pyexpat.ExpatError',
        'error'      : 'app_pyexpat.ExpatError',
        }

    interpleveldefs = {
        'ParserCreate':  'interp_pyexpat.ParserCreate',
        'XMLParserType': 'interp_pyexpat.W_XMLParserType',
        'ErrorString':   'interp_pyexpat.ErrorString',
        }

