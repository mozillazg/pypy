
'''libgdbm wrapper using ctypes'''

from __future__ import with_statement

#mport sys
import ctypes
import ctypes.util

class error(Exception):
    '''Exception for gdbm errors'''
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg  

    def __str__(self):
        return self.msg

class datum(ctypes.Structure):
    # pylint: disable=R0903
    # R0903: We don't need a lot of public methods
    '''Hold a c string (with explicit length - not null terminated) describing a key or value'''

    _fields_ = [
        ('dptr', ctypes.POINTER(ctypes.c_char)),
        ('dsize', ctypes.c_int),
        ]

    def __init__(self, text=None):
        #sys.stderr.write('blee creating a datum from %s\n' % text)
        if text is None:
            self.free_when_done = True
            self.dptr = None
            self.dsize = -1
            print 'No text, dptr is', bool(self.dptr)
        else:
            self.free_when_done = False
            if isinstance(text, str):
                ctypes.Structure.__init__(self, ctypes.create_string_buffer(text), len(text))
            else:
                raise TypeError, "text not None or str"

    def __nonzero__(self):
        if self.dptr:
            return True
        else:
            return False

    __bool__ = __nonzero__

    def __str__(self):
        char_star = ctypes.cast(self.dptr, ctypes.POINTER(ctypes.c_char))
        return char_star[:self.dsize]

    def __enter__(self):
        self.free_when_done = True
        return self

    def free(self):
        '''Free, in the style of C, the malloc'd memory associated with this datum (key or value)'''
        address = ctypes.cast(self.dptr, ctypes.POINTER(ctypes.c_char))
        FREE(address)
        
    def __exit__(self, *args):
        # pylint: disable=W0212
        # W0212: We seem to need _b_needsfree_

        # if dptr isn't a NULL pointer, free what it points at
        #sys.stderr.write('blee: self.dptr %s\n' % self.dptr)
        #sys.stderr.write('blee: dir(self.dptr) %s\n' % dir(self.dptr))
        # sys.stderr.write('blee: self.dptr.getcontents() %s\n' % self.dptr.getcontents())
        #sys.stderr.write('blee: ctypes.addressof(self.dptr) %s\n' % hex(ctypes.addressof(self.dptr)))
        #sys.stderr.write('blee: ctypes.byref(self.dptr) %s\n' % ctypes.byref(self.dptr))
        if self.free_when_done and self.dptr:
            self.free()

class dbm(object):
    '''A database object - providing access to gdbm tables'''
    def __init__(self, dbmobj):
        self._aobj = dbmobj

    def close(self):
        '''Close a table'''
        if not self._aobj:
            raise error('gdbm object has already been closed')
        # Note that gdbm_close will free the memory malloc'd for the open database (but not for keys or values)
        getattr(GDBM_LIB, FUNCS['close'])(self._aobj)
        self._aobj = None

    def __del__(self):
        if self._aobj:
            self.close()

    def keys(self):
        '''Get a list of the keys in the database'''
        if not self._aobj:
            raise error('gdbm object has already been closed')
        allkeys = []
        prior_key = getattr(GDBM_LIB, FUNCS['firstkey'])(self._aobj)
        while prior_key:
            key = str(prior_key)
            allkeys.append(key)
            new_key = getattr(GDBM_LIB, FUNCS['nextkey'])(self._aobj, prior_key)
            prior_key.free()
            prior_key = new_key
        return allkeys

    def get(self, key, default=None):
        '''Get a key from the table'''
        if not self._aobj:
            raise error('gdbm object has already been closed')
        key_datum = datum(key)
        with getattr(GDBM_LIB, FUNCS['fetch'])(self._aobj, key_datum) as value_datum:
            if value_datum:
                result = str(value_datum)
                return result
        return default

    def __len__(self):
        return len(self.keys())

    def __getitem__(self, key):
        # It's OK to use self.get here, because gdbm itself can never return a None;
        # It can only return strings (including the empty string), so None is a distinct sentinel value
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        if not self._aobj: 
            raise error('gdbm object has already been closed')
        key_datum = datum(key)
        value = datum(value)
        status = getattr(GDBM_LIB, FUNCS['store'])(self._aobj, key_datum, value, GDBM_LIB.DBM_REPLACE)
        return status

    def setdefault(self, key, default=''):
        '''Get and maybe set a default'''
        if not self._aobj:
            raise error('gdbm object has already been closed')
        value = self.get(key)
        if value is not None:
            return value
        status = self[key] = default
        if status < 0:
            raise error("cannot add item to database")
        return default

    def has_key(self, key):
        '''Does the table contain the requested key?'''
        if not self._aobj:
            raise error('gdbm object has already been closed')
        value = self.get(key)
        if value is None:
            return False
        else:
            return True

    def __delitem__(self, key):
        if not self._aobj:
            raise error('gdbm object has already been closed')
        key_datum = datum(key)
        status = getattr(GDBM_LIB, FUNCS['delete'])(self._aobj, key_datum)
        if status < 0:
            raise KeyError(key)

### initialization

def _init_func(name, argtypes=None, restype=None):
    '''Extract functions from libgdbm'''
    try:
        func = getattr(GDBM_LIB, '_gdbm_' + name)
        FUNCS[name] = '_gdbm_' + name
    except AttributeError:
        func = getattr(GDBM_LIB, 'gdbm_' + name)
        FUNCS[name] = 'gdbm_' + name
    if argtypes is not None:
        func.argtypes = argtypes
    if restype is not None:
        func.restype = restype

GDBM_LIBPATH = ctypes.util.find_library('gdbm')
if not GDBM_LIBPATH:
    raise ImportError("Cannot find gdbm library")
GDBM_LIB = ctypes.CDLL(GDBM_LIBPATH) # Linux

FUNCS = {}
_init_func('open', argtypes=(ctypes.c_char_p, ctypes.c_int, ctypes.c_int))
_init_func('close', restype=ctypes.c_void_p)
_init_func('firstkey', restype=datum)
_init_func('nextkey', argtypes=(ctypes.c_void_p, datum), restype=datum)
_init_func('fetch', restype=datum)
_init_func('store', restype=ctypes.c_int)
_init_func('delete', restype=ctypes.c_int)

C_LIBPATH = ctypes.util.find_library('c')
if not C_LIBPATH:
    raise ImportError("Cannot find c library")
C_LIB = ctypes.CDLL(C_LIBPATH) # Linux

try:
    FREE = getattr(C_LIB, '_free')
except AttributeError:
    FREE = getattr(C_LIB, 'free')
#FREE.argtypes = [ ctypes.POINTER(ctypes.c_char) ]
FREE.argtypes = [ ctypes.c_void_p ]
FREE.restype = None

GDBM_LIB.DBM_INSERT = 0
GDBM_LIB.DBM_REPLACE = 1

# pylint: disable=W0622
# W0622: We need to redefine open this time - it's part of the API
def open(filename, flag='r', mode=0666):
    "open a gdbm database"
    if not isinstance(filename, str):
        raise TypeError("expected string")

    openflag = 0

    gdbm_reader  = 0        # A reader.
    gdbm_writer  = 1        # A writer.
    gdbm_wrcreat = 2        # A writer.  Create the db if needed.
    gdbm_newdb   = 3        # A writer.  Always create a new db.

    try:
        openflag = {
            'r': gdbm_reader,
            'rw': gdbm_writer,
            'w': gdbm_writer,
            'c': gdbm_wrcreat,
            'n': gdbm_newdb,
            }[flag]
    except KeyError:
        raise error("arg 2 to open should be 'r', 'w', 'rw', 'c', or 'n'")

    #                                                filename, block_size, read_write, mode, fatal_func
    a_db = getattr(GDBM_LIB, FUNCS['open'])(filename, 2**18,         openflag,   mode, 0)
    if a_db == 0:
        raise error("Could not open file %s" % filename)
    return dbm(a_db)

__all__ = ('datum', 'dbm', 'error', 'open')

