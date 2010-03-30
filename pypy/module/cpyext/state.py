from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.lib.identity_dict import identity_dict
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import lltype


class State:
    def __init__(self, space):
        self.space = space
        self.reset()

    def reset(self):
        self.py_objects_w2r = {} # { w_obj -> raw PyObject }
        self.py_objects_r2w = {} # { addr of raw PyObject -> w_obj }
        self.borrow_mapping = {} # { addr of container -> { addr of containee -> None } }
        self.borrowed_objects = {} # { addr of containee -> None }
        self.non_heaptypes = [] # list of wrapped objects
        self.last_container = 0 # addr of last container
        self.exc_type = None
        self.exc_value = None

    def set_exception(self, w_type, w_value):
        self.clear_exception()
        self.exc_type = w_type
        self.exc_value = w_value

    def clear_exception(self):
        from pypy.module.cpyext.macros import Py_DECREF
        from pypy.module.cpyext.api import make_ref, ADDR
        # handling of borrowed objects, remove when we have
        # a weakkeydict
        exc_type = make_ref(self.space, self.exc_type, borrowed=True)
        if exc_type:
            Py_DECREF(self.space, exc_type)
            containee_ptr = rffi.cast(ADDR, exc_type)
            del self.borrowed_objects[containee_ptr]
        self.exc_type = None
        self.exc_value = None

    def check_and_raise_exception(self):
        exc_value = self.exc_value
        exc_type = self.exc_type
        if exc_type is not None or exc_value is not None:
            self.clear_exception()
            op_err = OperationError(exc_type, exc_value)
            raise op_err

    def print_refcounts(self):
        print "REFCOUNTS"
        for w_obj, obj in self.py_objects_w2r.items():
            print "%r: %i" % (w_obj, obj.c_ob_refcnt)
