from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, NoneNotWrapped
from pypy.interpreter.baseobjspace import W_Root

class CodecState(object):
    def __init__(self, space):
        self.codec_search_path = []
        self.codec_search_cache = {}
        self.codec_error_registry = {}
        self.codec_need_encodings = True

def register_codec(space, w_search_function):
    """register(search_function)
    
    Register a codec search function. Search functions are expected to take
    one argument, the encoding name in all lower case letters, and return
    a tuple of functions (encoder, decoder, stream_reader, stream_writer).
    """
    #import pdb; pdb.set_trace()
    state = space.fromcache(CodecState)
    if space.is_true(space.callable(w_search_function)):
        state.codec_search_path.append(w_search_function)
    else:
        raise OperationError(
            space.w_TypeError,
            space.wrap("argument must be callable"))
register_codec.unwrap_spec = [ObjSpace, W_Root]


def lookup_codec(space, encoding):
    """lookup(encoding) -> (encoder, decoder, stream_reader, stream_writer)
    Looks up a codec tuple in the Python codec registry and returns
    a tuple of functions.
    """
    #import pdb; pdb.set_trace()
    state = space.fromcache(CodecState)
    normalized_encoding = encoding.replace(" ", "-").lower()    
    w_result = state.codec_search_cache.get(normalized_encoding, None)
    if w_result is not None:
        return w_result
    if state.codec_need_encodings:
        w_import = space.getattr(space.builtin, space.wrap("__import__"))
        # registers new codecs
        space.call_function(w_import, space.wrap("encodings"))
        state.codec_need_encodings = False
        if len(state.codec_search_path) == 0:
            raise OperationError(
                space.w_LookupError,
                space.wrap("no codec search functions registered: "
                           "can't find encoding"))
    for w_search in state.codec_search_path:
        w_result = space.call_function(w_search,
                                       space.wrap(normalized_encoding))
        if not space.is_w(w_result, space.w_None):
            if not (space.is_true(space.is_(space.type(w_result),
                                            space.w_tuple)) and
                    space.int_w(space.len(w_result)) == 4):
                raise OperationError(
                    space.w_TypeError,
                    space.wrap("codec search functions must return 4-tuples"))
            else:
                state.codec_search_cache[normalized_encoding] = w_result 
                return w_result
    raise OperationError(
        space.w_LookupError,
        space.wrap("unknown encoding: %s" % encoding))
lookup_codec.unwrap_spec = [ObjSpace, str]
    

def lookup_error(space, errors):
    """lookup_error(errors) -> handler

    Return the error handler for the specified error handling name
    or raise a LookupError, if no handler exists under this name.
    """
    
    state = space.fromcache(CodecState)
    try:
        w_err_handler = state.codec_error_registry[errors]
    except KeyError:
        raise OperationError(
            space.w_LookupError,
            space.wrap("unknown error handler name %s" % errors))
    return w_err_handler
lookup_error.unwrap_spec = [ObjSpace, str]


def encode(space, w_obj, encoding=NoneNotWrapped, errors='strict'):
    """encode(obj, [encoding[,errors]]) -> object
    
    Encodes obj using the codec registered for encoding. encoding defaults
    to the default encoding. errors may be given to set a different error
    handling scheme. Default is 'strict' meaning that encoding errors raise
    a ValueError. Other possible values are 'ignore', 'replace' and
    'xmlcharrefreplace' as well as any other name registered with
    codecs.register_error that can handle ValueErrors.
    """
    if encoding is None:
        encoding = space.sys.defaultencoding
    w_encoder = space.getitem(lookup_codec(space, encoding), space.wrap(0))
    if space.is_true(w_encoder):
        w_res = space.call_function(w_encoder, w_obj, space.wrap(errors))
        return space.getitem(w_res, space.wrap(0))
    else:
        assert 0, "XXX, what to do here?"
encode.unwrap_spec = [ObjSpace, W_Root, str, str]

def decode(space, w_obj, encoding=NoneNotWrapped, errors='strict'):
    """decode(obj, [encoding[,errors]]) -> object

    Decodes obj using the codec registered for encoding. encoding defaults
    to the default encoding. errors may be given to set a different error
    handling scheme. Default is 'strict' meaning that encoding errors raise
    a ValueError. Other possible values are 'ignore' and 'replace'
    as well as any other name registerd with codecs.register_error that is
    able to handle ValueErrors.
    """
    if encoding is None:
        encoding = sys.getdefaultencoding()
    w_decoder = space.getitem(lookup_codec(space, encoding), space.wrap(1))
    if space.is_true(w_decoder):
        w_res = space.call_function(w_decoder, w_obj, space.wrap(errors))
        if (not space.is_true(space.isinstance(w_res, space.w_tuple))
            or space.int_w(space.len(w_res)) != 2):
            raise TypeError("encoder must return a tuple (object, integer)")
        return space.getitem(w_res, space.wrap(0))
    else:
        assert 0, "XXX, what to do here?"
decode.unwrap_spec = [ObjSpace, W_Root, str, str]

def register_error(space, errors, w_handler):
    """register_error(errors, handler)

    Register the specified error handler under the name
    errors. handler must be a callable object, that
    will be called with an exception instance containing
    information about the location of the encoding/decoding
    error and must return a (replacement, new position) tuple.
    """
    state = space.fromcache(CodecState)
    if space.is_true(space.callable(w_handler)):
        state.codec_error_registry[errors] = w_handler
    else:
        raise OperationError(
            space.w_TypeError,
            space.wrap("handler must be callable"))
register_error.unwrap_spec = [ObjSpace, str, W_Root]
