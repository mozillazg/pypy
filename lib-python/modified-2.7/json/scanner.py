"""JSON token scanner
"""
import re

__all__ = ['make_scanner']

NUMBER_RE = re.compile(
    r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?',
    (re.VERBOSE | re.MULTILINE | re.DOTALL))

def make_scanner(context):
    def _scan_once(string, idx):
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration

        if nextchar == '"':
            return context.parse_string(string, idx + 1, context.encoding, context.strict)
        elif nextchar == '{':
            return context.parse_object((string, idx + 1), context.encoding, context.strict,
                _scan_once, context.object_hook, context.object_pairs_hook)
        elif nextchar == '[':
            return context.parse_array((string, idx + 1), _scan_once)
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            return None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return False, idx + 5

        m = NUMBER_RE.match(string, idx)
        if m is not None:
            integer, frac, exp = m.groups()
            if frac or exp:
                res = context.parse_float(integer + (frac or '') + (exp or ''))
            else:
                res = context.parse_int(integer)
            return res, m.end()
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            return context.parse_constant('NaN'), idx + 3
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            return context.parse_constant('Infinity'), idx + 8
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            return context.parse_constant('-Infinity'), idx + 9
        else:
            raise StopIteration

    return _scan_once
