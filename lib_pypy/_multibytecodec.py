# indirection needed; otherwise the built-in module "_multibytecodec" shadows
# any file _multibytecodec.py that would be found in the user dirs
from __builtin__multibytecodec import *
from __builtin__multibytecodec import __getcodec
