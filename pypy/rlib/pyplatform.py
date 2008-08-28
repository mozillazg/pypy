
""" This file contains various platform-specific profiles for
pypy's cross compilation
"""

import py

class Platform(object):
    def get_compiler(self):
        return None

    def execute(self, cmd):
        return py.process.cmdexec(cmd)

    # platform objects are immutable

    def __hash__(self):
        return hash(self.__class__.__name__)

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        return self.__class__.__name__ == other.__class__.__name__

class Maemo(Platform):
    def get_compiler(self):
        return '/scratchbox/compilers/cs2005q3.2-glibc-arm/bin/sbox-arm-linux-gcc'
    
    def execute(self, cmd):
        return py.process.cmdexec('/scratchbox/login ' + cmd)
