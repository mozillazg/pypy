from pypy.interpreter import threadlocals

class ExecutionContext:
    """An ExecutionContext holds the state of an execution thread
    in the Python interpreter."""
    
    def __init__(self, space):
        # Note that self.framestack only contains PyFrames
        self.space = space
        self.framestack = Stack()

    def enter(self, frame):
        locals = threadlocals.getlocals()
        self.framestack.push(frame)
        previous_ec = locals.executioncontext
        locals.executioncontext = self
        return previous_ec

    def leave(self, previous_ec):
        locals.executioncontext = previous_ec
        self.framestack.pop()

    def get_w_builtins(self):
        if self.framestack.empty():
            return self.space.w_builtins
        else:
            return self.framestack.top().w_builtins

    def make_standard_w_globals(self):
        "Create a new empty 'globals' dictionary."
        w_key = self.space.wrap("__builtins__")
        w_value = self.get_w_builtins()
        w_globals = self.space.newdict([(w_key, w_value)])
        return w_globals

    def bytecode_trace(self, frame):
        "Trace function called before each bytecode."

    def exception_trace(self, operationerr):
        "Trace function called upon OperationError."
        operationerr.record_interpreter_traceback()
        #operationerr.print_detailed_traceback(self.space)

    def sys_exc_info(self):
        """Implements sys.exc_info().
        Return an OperationError instance or None."""
        for i in range(self.framestack.depth()):
            frame = self.framestack.top(i)
            if frame.last_exception is not None:
                return frame.last_exception
        return None


class Stack:
    """Utility class implementing a stack."""

    def __init__(self):
        self.items = []

    def clone(self):
        s = self.__class__()
        for item in self.items:
            try:
                item = item.clone()
            except AttributeError:
                pass
            s.push(item)
        return s

    def push(self, item):
        self.items.append(item)

    def pop(self):
        return self.items.pop()

    def top(self, position=0):
        """'position' is 0 for the top of the stack, 1 for the item below,
        and so on.  It must not be negative."""
        return self.items[~position]

    def depth(self):
        return len(self.items)

    def empty(self):
        return not self.items
