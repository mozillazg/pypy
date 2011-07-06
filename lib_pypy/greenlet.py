import tealet, sys

# ____________________________________________________________
# Exceptions

class GreenletExit(Exception):
    """This special exception does not propagate to the parent greenlet; it
can be used to kill a single greenlet."""

error = tealet.error

# ____________________________________________________________
# Helper function

def getcurrent():
    "Returns the current greenlet (i.e. the one which called this function)."
    try:
        return _tls.current
    except AttributeError:
        # first call in this thread: current == main
        _green_create_main()
        return _tls.current

# ____________________________________________________________
# The 'greenlet' class

class greenlet(object):
    getcurrent = staticmethod(getcurrent)
    error = error
    GreenletExit = GreenletExit

    def __new__(cls, *args, **kwds):
        self = super(greenlet, cls).__new__(cls, *args, **kwds)
        self.__parent = getcurrent()
        return self

    def __init__(self, run=None, parent=None):
        if run is not None:
            self.run = run
        if parent is not None:
            self.parent = parent

    def switch(self, *args):
        "switch execution to greenlet optionally passing a value, "
        "return value passed when switching back"
        _tls.passaround = args
        oldcurrent = _tls.current
        target = self
        while True:
            if target.__state_active():
                target.__tealet.switch()
                break
            if not target.__state_started():
                g = _GreenTealet()
                g.greenlet = target
                _tls.maintealet.start(g)
                break
            target = target.__parent
        #
        _tls.current = oldcurrent
        res = _tls.passaround
        _tls.passaround = None
        if _tls.passaround_exception is not None:
            typ, val, tb = _tls.passaround_exception
            _tls.passaround_exception = None
            raise typ, val, tb
        if len(res) == 1:
            res = res[0]
        return res

    def throw(self, typ=GreenletExit, val=None, tb=None):
        "raise exception in greenlet, return value passed when switching back"
        if self.__is_dead():
            # dead greenlet: turn GreenletExit into a regular return
            if (isinstance(typ, type(GreenletExit)) and
                issubclass(typ, GreenletExit)):
                if val is None:
                    return self.switch(typ())
                if isinstance(val, GreenletExit):
                    return self.switch(val)
            if isinstance(typ, GreenletExit):
                return self.switch(typ)
        #
        _tls.passaround_exception = (typ, val, tb)
        return self.switch()

    def __state_started(self):
        return hasattr(self, '_greenlet__tealet')

    def __state_active(self):
        return getattr(self, '_greenlet__tealet', None) is not None

    def __nonzero__(self):
        return self.__state_active()

    def __get_parent(self):
        return self.__parent

    def __set_parent(self, nparent):
        if not isinstance(nparent, greenlet):
            raise TypeError("parent must be a greenlet")
        p = nparent
        while p is not None:
            if p is self:
                raise ValueError("cyclic parent chain")
            p = p.__parent
        self.__parent = nparent

    def __get_gr_frame(self):
        raise NotImplementedError("attribute 'gr_frame' of greenlet objects")

    def __is_dead(self):
        return self.__state_started() and not self.__state_active()

    parent   = property(__get_parent, __set_parent)
    gr_frame = property(__get_gr_frame)
    dead     = property(__is_dead)

# ____________________________________________________________
# Internal stuff

try:
    from thread import _local
except ImportError:
    class _local(object):    # assume no threads
        pass

_tls = _local()

def _green_create_main():
    # create the main greenlet for this thread
    _tls.maintealet = tealet.MainTealet()
    _tls.current = None
    _tls.passaround_exception = None
    gmain = greenlet()
    gmain._greenlet__tealet = _tls.maintealet
    _tls.current = gmain

class _GreenTealet(tealet.Tealet):
    def run(self):
        while True:
            g = self.greenlet
            g._greenlet__tealet = self
            try:
                try:
                    _tls.current = g
                    args = _tls.passaround
                    _tls.passaround = None
                    if _tls.passaround_exception is not None:
                        typ, val, tb = _tls.passaround_exception
                        _tls.passaround_exception = None
                        raise typ, val, tb
                    res = self.greenlet.run(*args)
                except GreenletExit, res:
                    pass
                except:
                    _tls.passaround_exception = sys.exc_info()
                    res = None
            finally:
                g._greenlet__tealet = None
            _tls.passaround = (res,)
            parent = g._greenlet__parent
            while True:
                if parent._greenlet__state_active():
                    return parent._greenlet__tealet
                if parent._greenlet__state_started():
                    parent = parent._greenlet__parent    # dead, try the parent
                else:
                    # not started yet.  Start it now.
                    self.greenlet = parent
                    break
