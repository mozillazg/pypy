"""Utilities for use with the pure Python _sre module."""
import imp, os.path, sys
try:
    set
except NameError:
    from sets import Set as set

from sre_constants import OPCODES
OPCODES = dict([(value, key) for key, value in OPCODES.items()])
WIDE_OPS = set(["info", "in", "in_ignore", "branch", "repeat_one",
    "min_repeat_one", "repeat", "assert", "assert_not"])
UNARY_OPS = set(["success", "any", "any_all", "failure", "max_until",
    "min_until"])

def import_sre_py():
    """This forces the _sre.py to be imported as the _sre modules, also on
    CPython systems with an existing _sre extension module. This must be called
    before importing the re module. It's assumed that _sre.py is in the same
    directory as _sre_support.py."""
    module_path = os.path.dirname(__file__)
    _sre = imp.load_module("_sre", *imp.find_module("_sre", [module_path]))
    sys.modules["_sre"] = _sre

def opcodes(pattern, flags=0):
    """Returns the list of plain numeric bytecodes for a pattern string."""
    import_sre_py()
    import re
    return re.compile(pattern, flags)._code

def dis(pattern, flags=0):
    """Prints a symbolic representation of the bytecodes for a pattern."""
    dis_opcodes(opcodes(pattern, flags))

def dis_opcodes(code):
    symbolic_list = []
    i = 0
    while i < len(code):
        symbol = OPCODES[code[i]]
        if symbol in UNARY_OPS:
            symbolic_list.append(symbol)
            i += 1
        else:
            if symbol in WIDE_OPS:
                skip = code[i + 1]
            elif symbol == "groupref_exists":
                skip = code[i + 2]
            else:
                skip = 1
            symbolic_list.append("%s %s" % (symbol, code[i + 1:i + 1 + skip]))
            i += skip + 1

    print "\n".join(symbolic_list)
