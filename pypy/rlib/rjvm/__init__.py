def initialize():
    """Initialize JPype."""
    import atexit
    import os.path
    import jpype

    this_dir = os.path.dirname(__file__)
    rlib_dir = os.path.join(this_dir, 'java')
    jpype.startJVM(jpype.getDefaultJVMPath(),
                   '-ea',
                   '-Djava.class.path=%s' % os.path.abspath(rlib_dir))

    def cleanup():
        jpype.shutdownJVM()

    atexit.register(cleanup)

initialize()
del initialize

# When JPype is initialized, import all the code. Some of it will be using
# JPype, so it has to be initialized.

from api import *



