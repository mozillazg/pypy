
""" This file is responsible for faking types
"""

class GetSetDescriptor(object):
    def __init__(self, protocol):
        self.protocol = protocol

    def __get__(self, obj, type=None):
        return self.protocol.get(obj, type)

    def __set__(self, obj, value):
        self.protocol.set(obj, value)

class GetDescriptor(object):
    def __init__(self, protocol):
        self.protocol = protocol

    def __get__(self, obj, type=None):
        return self.protocol.get(obj, type)

# these are one-go functions for wrapping/unwrapping types,
# note that actual caching is defined in other files,
# this is only the case when we *need* to wrap/unwrap
# type

def wrap_type(tp):
    pass

def unwrap_type(name, bases_w, dict_w):
    pass
