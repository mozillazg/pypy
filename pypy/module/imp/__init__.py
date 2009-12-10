from pypy.interpreter.mixedmodule import MixedModule

names = ['C_BUILTIN', 'C_EXTENSION', 'IMP_HOOK', 'NullImporter', 'PKG_DIRECTORY',
 'PY_CODERESOURCE', 'PY_COMPILED', 'PY_FROZEN', 'PY_RESOURCE', 'PY_SOURCE',
 'SEARCH_ERROR', '__doc__', '__name__', '__package__', 'acquire_lock', 'find_module',
 'get_frozen_object', 'get_magic', 'get_suffixes', 'init_builtin', 'init_frozen',
 'is_builtin', 'is_frozen', 'load_compiled', 'load_dynamic', 'load_module',
 'load_package', 'load_source', 'lock_held', 'new_module', 'release_lock', 'reload']


class Module(MixedModule):
    """
    This module provides the components needed to build your own
    __import__ function.
    """
    interpleveldefs = {
        'PY_SOURCE':       'space.wrap(importing.PY_SOURCE)',
        'PY_COMPILED':     'space.wrap(importing.PY_COMPILED)',
        'PKG_DIRECTORY':   'space.wrap(importing.PKG_DIRECTORY)',
        'C_BUILTIN':       'space.wrap(importing.C_BUILTIN)',
        'get_suffixes':    'interp_imp.get_suffixes',

        'get_magic':       'interp_imp.get_magic',
        'find_module':     'interp_imp.find_module',
        'load_module':     'interp_imp.load_module',
        'load_source':     'interp_imp.load_source',
        'load_compiled':   'interp_imp.load_compiled',
        #'run_module':      'interp_imp.run_module',
        'new_module':      'interp_imp.new_module',
        'init_builtin':    'interp_imp.init_builtin',
        'init_frozen':     'interp_imp.init_frozen',
        'is_builtin':      'interp_imp.is_builtin',
        'is_frozen':       'interp_imp.is_frozen',
        }

    appleveldefs = {
        }

# PyPy-specific interface
try:
    import __pypy__
    def get_magic():
        """Return the magic number for .pyc or .pyo files."""
        import struct
        return struct.pack('<i', __pypy__.PYC_MAGIC)
except ImportError:
    # XXX CPython testing hack: delegate to the real imp.get_magic
    get_magic = __import__('imp').get_magic

def get_suffixes():
    """Return a list of (suffix, mode, type) tuples describing the files
    that find_module() looks for."""
    return [('.py', 'U', PY_SOURCE),
            ('.pyc', 'rb', PY_COMPILED)]


def find_module(name, path=None):
    """find_module(name, [path]) -> (file, filename, (suffix, mode, type))
    Search for a module.  If path is omitted or None, search for a
    built-in, frozen or special module and continue search in sys.path.
    The module name cannot contain '.'; to search for a submodule of a
    package, pass the submodule name and the package's __path__.
    """
    if path is None:
        if name in sys.builtin_module_names:
            return (None, name, ('', '', C_BUILTIN))
        path = sys.path
    for base in path:
        filename = os.path.join(base, name)
        if os.path.isdir(filename):
            return (None, filename, ('', '', PKG_DIRECTORY))
        for ext, mode, kind in get_suffixes():
            if os.path.exists(filename+ext):
                return (file(filename+ext, mode), filename+ext, (ext, mode, kind))
    raise ImportError, 'No module named %s' % (name,)


def load_module(name, file, filename, description):
    """Load a module, given information returned by find_module().
    The module name must include the full package name, if any.
    """
    suffix, mode, type = description

    if type == PY_SOURCE:
        return load_source(name, filename, file)

    if type == PKG_DIRECTORY:
        initfilename = os.path.join(filename, '__init__.py')
        module = sys.modules.setdefault(name, new_module(name))
        module.__name__ = name
        module.__doc__ = None
        module.__file__ = initfilename
        module.__path__ = [filename]
        execfile(initfilename, module.__dict__)
        return module

    if type == C_BUILTIN:
        module = __import__(name, {}, {}, None)
        return module
    if type == PY_COMPILED:
       return  load_compiled(name, filename, file)
    raise ValueError, 'invalid description argument: %r' % (description,)

def load_dynamic(name, *args, **kwds):
    raise ImportError(name)

def load_source(name, pathname, file=None):
    autoopen = file is None
    if autoopen:
        file = open(pathname, 'U')
    source = file.read()
    if autoopen:
        file.close()
    co = compile(source, pathname, 'exec')
    return run_module(name, pathname, co)

def load_compiled(name, pathname, file=None):
    import marshal
    autoopen = file is None
    if autoopen:
        file = open(pathname, 'rb')
    magic = file.read(4)
    if magic != get_magic():
        raise ImportError("Bad magic number in %s" % pathname)
    file.read(4)    # skip timestamp
    co = marshal.load(file)
    if autoopen:
        file.close()
    return run_module(name, pathname, co)

def run_module(name, pathname, co):
    module = sys.modules.setdefault(name, new_module(name))
    module.__name__ = name
    module.__doc__ = None
    module.__file__ = pathname
    try:
        exec co in module.__dict__
    except :
        sys.modules.pop(name,None)
        raise
    return module
 

def new_module(name):
    """Create a new module.  Do not enter it in sys.modules.
    The module name must include the full package name, if any.
    """
    return new.module(name)


def init_builtin(name):
    if name not in sys.builtin_module_names:
        return None
    if name in sys.modules:
        raise ImportError("cannot initialize a built-in module twice "
                          "in PyPy")
    return __import__(name)

def init_frozen(name):
    return None

def is_builtin(name):
    if name in sys.builtin_module_names:
        return -1   # cannot be initialized again
    else:
        return 0

def is_frozen(name):
    return False

# ____________________________________________________________

try:
    # PyPy-specific interface
    from thread import _importlock_held    as lock_held
    from thread import _importlock_acquire as acquire_lock
    from thread import _importlock_release as release_lock
except ImportError:
    def lock_held():
        """On platforms without threads, return False."""
        return False
    def acquire_lock():
        """On platforms without threads, this function does nothing."""
    def release_lock():
        """On platforms without threads, this function does nothing."""
