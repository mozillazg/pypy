from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import NoValue
from pypy.interpreter.eval import Frame
from pypy.interpreter.pyframe import ControlFlowException, ExitFrame

#
# Generator support. Note that GeneratorFrame is not a subclass of PyFrame.
# PyCode objects use a custom subclass of both PyFrame and GeneratorFrame
# when they need to interpret Python bytecode that is a generator.
# Otherwise, GeneratorFrame could also be used to define, say,
# built-in generators (which are usually done in CPython as functions
# that return iterators).
#

class GeneratorFrame(Frame):
    "A frame attached to a generator."

    def run(self):
        "Build a generator-iterator."
        self.exhausted = False
        return GeneratorIterator(self)

    ### extra opcodes ###

    # XXX mmmh, GeneratorFrame is supposed to be independent from
    # Python bytecode... Well, it is. These are not used when
    # GeneratorFrame is used with other kinds of Code subclasses.

    def RETURN_VALUE(f):  # overridden
        raise SGeneratorReturn()

    def YIELD_VALUE(f):
        w_yieldedvalue = f.valuestack.pop()
        raise SYieldValue(w_yieldedvalue)
    YIELD_STMT = YIELD_VALUE  # misnamed in old versions of dis.opname


class GeneratorIterator(object):
    "An iterator created by a generator."
    
    def __init__(self, frame):
        self.frame = frame
        self.running = False

    def nextvalue(self):
        # raise NoValue when exhausted
        if self.running:
            space = self.frame.space
            raise OperationError(space.w_ValueError,
                                 space.wrap('generator already executing'))
        if self.frame.exhausted:
            raise NoValue
        self.running = True
        try:
            return Frame.run(self.frame)
        finally:
            self.running = False


    # XXX trick for trivialobjspace
    # XXX make these __iter__() and next() app-visible

    def __iter__(self):
        return self

    def next(self):
        # XXX trivialobjspace only !!
        try:
            return self.nextvalue()
        except NoValue:
            raise StopIteration

#
# the specific ControlFlowExceptions used by generators
#

class SYieldValue(ControlFlowException):
    """Signals a 'yield' statement.
    Argument is the wrapped object to return."""
    def action(self, frame, last_instr, executioncontext):
        w_yieldvalue = self.args[0]
        raise ExitFrame(w_yieldvalue)

class SGeneratorReturn(ControlFlowException):
    """Signals a 'return' statement inside a generator."""
    def emptystack(self, frame):
        frame.exhausted = True
        raise NoValue
