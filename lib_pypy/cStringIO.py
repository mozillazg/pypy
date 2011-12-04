# indirection needed; otherwise the built-in module "cStringIO" shadows
# any file cStringIO.py that would be found in the user dirs

try:
    from __builtin_cStringIO import *

except ImportError:
    #
    # StringIO-based cStringIO implementation.
    #
    from StringIO import *
    from StringIO import __doc__

    class StringIO(StringIO):
        def reset(self):
            """
            reset() -- Reset the file position to the beginning
            """
            self.seek(0, 0)
