"""
Processor auto-detection
"""
import sys, os


class ProcessorAutodetectError(Exception):
    pass

x86_backend = 'i386'

def autodetect():
    mach = None
    try:
        import platform
        mach = platform.machine()
    except ImportError:
        pass
    if not mach:
        platform = sys.platform.lower()
        if platform.startswith('win'):   # assume an Intel Windows
            return x86_backend
        # assume we have 'uname'
        mach = os.popen('uname -m', 'r').read().strip()
        if not mach:
            raise ProcessorAutodetectError, "cannot run 'uname -m'"
    if mach == 'x86_64' and sys.maxint == 2147483647:
        mach = 'x86'     # it's a 64-bit processor but in 32-bits mode, maybe
    try:
        return {'i386': x86_backend,
                'i486': x86_backend,
                'i586': x86_backend,
                'i686': x86_backend,
                'i86pc': x86_backend,    # Solaris/Intel
                'x86':   x86_backend,    # Apple
                'Power Macintosh': 'ppc', 
                }[mach]
    except KeyError:
        raise ProcessorAutodetectError, "unsupported processor '%s'" % mach
