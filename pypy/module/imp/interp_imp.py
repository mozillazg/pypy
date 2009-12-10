from pypy.module.imp import importing
from pypy.module._file.interp_file import W_File
from pypy.rlib import streamio
from pypy.interpreter.error import OperationError
from pypy.interpreter.module import Module
from pypy.interpreter.gateway import NoneNotWrapped
import struct

def get_suffixes(space):
    w = space.wrap
    return space.newlist([
        space.newtuple([w('.py'), w('U'), w(importing.PY_SOURCE)]),
        space.newtuple([w('.pyc'), w('rb'), w(importing.PY_COMPILED)]),
        ])

def get_magic(space):
    return space.wrap(struct.pack('<i', importing.get_pyc_magic(space)))

def get_file(space, w_file, filename, filemode):
    if w_file is None or space.is_w(w_file, space.w_None):
        return streamio.open_file_as_stream(filename, filemode)
    else:
        return space.interp_w(W_File, w_file).stream

def find_module(space, w_name, w_path=None):
    name = space.str_w(w_name)
    if space.is_w(w_path, space.w_None):
        w_path = space.sys.get('path')

    import_info, _ = importing.find_module(
        space, name, w_name, name, w_path, use_loader=False)
    if import_info is None:
        raise OperationError(
            space.w_ImportError,
            space.wrap("No module named %s" % (name,)))
    modtype, filename, stream, suffix, filemode = import_info

    w_filename = space.wrap(filename)

    if stream is not None:
        fileobj = W_File(space)
        fileobj.fdopenstream(
            stream, stream.try_to_find_file_descriptor(),
            filemode, w_filename)
        w_fileobj = space.wrap(fileobj)
    else:
        w_fileobj = space.w_None
    w_import_info = space.newtuple(
        [space.wrap(suffix), space.wrap(filemode), space.wrap(modtype)])
    return space.newtuple([w_fileobj, w_filename, w_import_info])

def load_module(space, w_name, w_file, w_filename, w_info):
    w_suffix, w_filemode, w_modtype = space.unpackiterable(w_info)

    filename = space.str_w(w_filename)
    filemode = space.str_w(w_filemode)
    if space.is_w(w_file, space.w_None):
        stream = None
    else:
        stream = get_file(space, w_file, filename, filemode)

    import_info = (space.int_w(w_modtype),
                   filename,
                   stream,
                   space.str_w(w_suffix),
                   filemode)
    return importing.load_module(
        space, w_name, import_info, None)

def load_source(space, w_modulename, w_filename, w_file=None):
    filename = space.str_w(w_filename)

    stream = get_file(space, w_file, filename, 'U')

    w_mod = space.wrap(Module(space, w_modulename))
    space.sys.setmodule(w_mod)
    space.setattr(w_mod, space.wrap('__file__'), w_filename)
    space.setattr(w_mod, space.wrap('__doc__'), space.w_None)

    importing.load_source_module(
        space, w_modulename, w_mod, filename, stream.readall())
    if space.is_w(w_file, space.w_None):
        stream.close()
    return w_mod

def load_compiled(space, w_modulename, w_filename, w_file=None):
    filename = space.str_w(w_filename)

    stream = get_file(space, w_file, filename, 'rb')

    w_mod = space.wrap(Module(space, w_modulename))
    space.sys.setmodule(w_mod)
    space.setattr(w_mod, space.wrap('__file__'), w_filename)
    space.setattr(w_mod, space.wrap('__doc__'), space.w_None)

    magic = importing._r_long(stream)
    timestamp = importing._r_long(stream)

    importing.load_compiled_module(
        space, w_modulename, w_mod, filename, magic, timestamp,
        stream.readall())
    if space.is_w(w_file, space.w_None):
        stream.close()
    return w_mod

def new_module(space, w_name):
    return space.wrap(Module(space, w_name))

def init_builtin(space, w_name):
    name = space.str_w(w_name)
    if name not in space.builtin_modules:
        return
    if space.finditem(space.sys.get('modules'), w_name) is not None:
        raise OperationError(
            space.w_ImportError,
            space.wrap("cannot initialize a built-in module twice in PyPy"))
    return space.getbuiltinmodule(name)

def init_frozen(space, w_name):
    return None

def is_builtin(space, w_name):
    name = space.str_w(w_name)
    if name not in space.builtin_modules:
        return space.wrap(0)
    if space.finditem(space.sys.get('modules'), w_name) is not None:
        return space.wrap(-1)   # cannot be initialized again
    return space.wrap(1)

def is_frozen(space, w_name):
    return space.w_False
