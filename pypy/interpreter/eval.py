"""
This module defines the abstract base classes that support execution:
Code and Frame.
"""


class Code(object):
    """A code is a compiled version of some source code.
    Abstract base class."""

    def __init__(self, co_name):
        self.co_name = co_name

    def create_frame(self, space):
        "Create an empty frame object suitable for evaluation of this code."
        raise TypeError, "abstract"

    def exec_code(self, space, w_globals, w_locals):
        "Implements the 'exec' statement."
        frame = self.create_frame(space)
        frame.setglobaldict(w_globals)
        frame.setlocaldict(w_locals)
        frame.setclosure(None)
        return frame.run()

    def signature(self):
        "([list-of-arg-names], vararg-name-or-None, kwarg-name-or-None)."
        return [], None, None

    def getargcount(self):
        "Number of arguments including * and **."
        argnames, varargname, kwargname = self.signature()
        count = len(argnames)
        if varargname is not None:
            count += 1
        if kwargname is not None:
            count += 1
        return count

    def getlocalvarname(self, index):
        "Default implementation, can be overridden."
        argnames, varargname, kwargname = self.signature()
        try:
            return argnames[index]
        except IndexError:
            index -= len(argnames)
            if varargname is not None:
                if index == 0:
                    return varargname
                index -= 1
            if kwargname is not None:
                if index == 0:
                    return kwargname
                index -= 1
            raise IndexError, "local variable index out of bounds"


class Frame(object):
    """A frame is an environment supporting the execution of a code object.
    Abstract base class."""

    def __init__(self, space, code):
        self.space      = space
        self.code       = code       # Code instance
        self.w_globals  = None       # wrapped dict of globals
        self.w_locals   = None       # wrapped dict of locals

    def run(self):
        "Run the frame."
        executioncontext = self.space.getexecutioncontext()
        previous = executioncontext.enter(self)
        try:
            result = self.eval(executioncontext)
        finally:
            executioncontext.leave(previous)
        return result

    def eval(self, executioncontext):
        "Abstract method to override."
        raise TypeError, "abstract"

    def getglobaldict(self):
        return self.w_globals

    def setglobaldict(self):
        self.w_globals = w_globals

    def getlocaldict(self):
        "Overriden by subclasses with another representation for locals."
        return self.w_locals

    def setlocaldict(self, w_locals):
        """Initialize the locals from a dictionary.
        Overriden by subclasses with another representation for locals."""
        self.w_locals = w_locals

    def getlocalvar(self, index):
        """Get the value of the indexth local variable
        where numbering is according to self.code.signature().
        Default implementation, to be overridden."""
        varname = self.code.getlocalvarname(index)
        return self.space.getitem(w_locals, self.space.wrap(varname))

    def setlocalvar(self, index, w_value):
        """Set the value of the indexth local variable,
        where numbering is according to self.code.signature().
        Default implementation, to be overridden."""
        if self.w_locals is None:
            self.w_locals = self.space.newdict([])
        varname = self.code.getlocalvarname(index)
        self.space.setitem(self.w_locals, self.space.wrap(varname), w_value)

    def setclosure(self, closure):
        """Initialize the closure from the given data, which should be None or
        a list of Cells for PyFrame.  This should be called after setlocalvar()
        or setlocaldict() is used to initialize the frame."""
        if closure:
            raise TypeError, "%s instance expects no closure" % self.__class__
