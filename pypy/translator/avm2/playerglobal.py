import sys
from pypy.translator.avm2.library import get_playerglobal
playerglobal = get_playerglobal()
sys.modules[__name__] = playerglobal
