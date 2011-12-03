# indirection needed; otherwise the built-in module "_socket" shadows
# any file _socket.py that would be found in the user dirs
from __builtin__socket import *
