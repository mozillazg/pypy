
""" The file that keeps track about freed/kept-alive objects allocated
by _rawffi. Used for debugging ctypes
"""
from rpython.rlib.objectmodel import we_are_translated


class Tracker(object):
    DO_TRACING = True

    def __init__(self):
        self.alloced = {}

    def do_tracing(self):
        return not we_are_translated() and self.DO_TRACING

    def trace_allocation(self, address, obj):
        if not we_are_translated():
            self.alloced[address] = None

    def trace_free(self, address):
        if not we_are_translated():
            if address in self.alloced:
                del self.alloced[address]

# single, global, static object to keep all tracker info
tracker = Tracker()

def num_of_allocated_objects(space):
    return space.wrap(len(tracker.alloced))

def print_alloced_objects(space):
    xxx
    # eventually inspect and print what's left from applevel
