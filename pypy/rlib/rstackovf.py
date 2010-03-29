
# RPython raises StackOverflow instead of just RuntimeError when running
# out of C stack.  We need some hacks to support "except StackOverflow:"
# in untranslated code too.  This StackOverflow has a strange shape in
# order to be special-cased by the flow object space (it is replaced by
# the class StackOverflow).

class StackOverflow(RuntimeError):
    """Out of C stack."""

# rename the variable, but the name of the class is still StackOverflow
_StackOverflow = StackOverflow

# replace StackOverflow with this, which works in untranslated code too
StackOverflow = ((RuntimeError, RuntimeError),)
