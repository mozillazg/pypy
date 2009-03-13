from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError
from pypy.objspace.descroperation import object_setattr
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo

import sys

if sys.platform == "win32":
    libname = 'libexpat'
else:
    libname = 'expat'
eci = ExternalCompilationInfo(
        libraries=[libname],
        includes=['expat.h']
    )
eci = rffi_platform.configure_external_library(
    libname, eci,
    [dict(prefix='expat-',
          include_dir='lib', library_dir='win32/bin/release'),
     ])

class CConfigure:
    _compilation_info_ = eci
    XML_Content = rffi_platform.Struct('XML_Content',[
        ('numchildren', rffi.INT),
        ('children', rffi.VOIDP),
        ('name', rffi.CCHARP),
        ('type', rffi.INT),
        ('quant', rffi.INT),
    ])
    XML_FALSE = rffi_platform.ConstantInteger('XML_FALSE')
    XML_TRUE = rffi_platform.ConstantInteger('XML_TRUE')
XML_Parser = rffi.VOIDP # an opaque pointer

for k, v in rffi_platform.configure(CConfigure).items():
    globals()[k] = v


def expat_external(*a, **kw):
    kw['compilation_info'] = eci
    return rffi.llexternal(*a, **kw)

HANDLERS = dict(
    StartElementHandler = [rffi.CCHARP, rffi.CCHARPP],
    EndElementHandler = [rffi.CCHARP],
    ProcessingInstructionHandler = [rffi.CCHARP, rffi.CCHARP],
    CharacterDataHandler = [rffi.CCHARP, rffi.INT],
    UnparsedEntityDeclHandler = [rffi.CCHARP] * 5,
    NotationDeclHandler = [rffi.CCHARP] * 4,
    StartNamespaceDeclHandler = [rffi.CCHARP, rffi.CCHARP],
    EndNamespaceDeclHandler = [rffi.CCHARP],
    CommentHandler = [rffi.CCHARP],
    StartCdataSectionHandler = [],
    EndCdataSectionHandler = [],
    DefaultHandler = [rffi.CCHARP, rffi.INT],
    DefaultHandlerExpand = [rffi.CCHARP, rffi.INT],
    NotStandaloneHandler = [],
    ExternalEntityRefHandler = [rffi.CCHARP] * 4,
    StartDoctypeDeclHandler = [rffi.CCHARP, rffi.CCHARP, rffi.CCHARP, rffi.INT],
    EndDoctypeDeclHandler = [],
    EntityDeclHandler = [rffi.CCHARP, rffi.INT, rffi.CCHARP, rffi.INT,
                         rffi.CCHARP, rffi.CCHARP, rffi.CCHARP, rffi.CCHARP],
    XmlDeclHandler = [rffi.CCHARP, rffi.CCHARP, rffi.INT],
    ElementDeclHandler = [rffi.CCHARP, lltype.Ptr(XML_Content)],
    AttlistDeclHandler = [rffi.CCHARP] * 4 + [rffi.INT],
    )
if True: #XML_COMBINED_VERSION >= 19504:
    HANDLERS['SkippedEntityHandler'] = [rffi.CCHARP, rffi.INT]

SETTERS = {}
for name, params in HANDLERS.items():
    c_name = 'XML_Set' + name
    if name in ['UnknownEncodingHandler',
                'ExternalEntityRefHandler',
                'NotStandaloneHandler']:
        RESULT_TYPE = rffi.INT
    else:
        RESULT_TYPE = lltype.Void
    CALLBACK = lltype.Ptr(lltype.FuncType(
        [rffi.VOIDP] + params, RESULT_TYPE))
    func = expat_external(c_name,
                          [XML_Parser, CALLBACK], rffi.INT)
    SETTERS[name] = func

XML_ParserCreate = expat_external(
    'XML_ParserCreate', [rffi.CCHARP], XML_Parser)
XML_ParserCreateNS = expat_external(
    'XML_ParserCreateNS', [rffi.CCHARP, rffi.CHAR], XML_Parser)
XML_Parse = expat_external(
    'XML_Parse', [XML_Parser, rffi.CCHARP, rffi.INT, rffi.INT], rffi.INT)
XML_StopParser = expat_external(
    'XML_StopParser', [XML_Parser, rffi.INT], lltype.Void)

XML_SetReturnNSTriplet = expat_external(
    'XML_SetReturnNSTriplet', [XML_Parser, rffi.INT], lltype.Void)
XML_GetSpecifiedAttributeCount = expat_external(
    'XML_GetSpecifiedAttributeCount', [XML_Parser], rffi.INT)

XML_GetErrorCode = expat_external(
    'XML_GetErrorCode', [XML_Parser], rffi.INT)
XML_ErrorString = expat_external(
    'XML_ErrorString', [rffi.INT], rffi.CCHARP)
XML_GetCurrentLineNumber = expat_external(
    'XML_GetCurrentLineNumber', [XML_Parser], rffi.INT)
XML_GetErrorLineNumber = XML_GetCurrentLineNumber
XML_GetCurrentColumnNumber = expat_external(
    'XML_GetCurrentColumnNumber', [XML_Parser], rffi.INT)
XML_GetErrorColumnNumber = XML_GetCurrentColumnNumber
XML_GetCurrentByteIndex = expat_external(
    'XML_GetCurrentByteIndex', [XML_Parser], rffi.INT)
XML_GetErrorByteIndex = XML_GetCurrentByteIndex

XML_FreeContentModel = expat_external(
    'XML_FreeContentModel', [XML_Parser, lltype.Ptr(XML_Content)], lltype.Void)


class W_XMLParserType(Wrappable):

    def __init__(self, encoding, namespace_separator, w_intern):
        if encoding:
            self.encoding = encoding
        else:
            self.encoding = 'utf-8'
        self.namespace_separator = namespace_separator

        self.w_intern = w_intern

        self.returns_unicode = True
        self.ordered_attributes = False
        self.specified_attributes = False

        if namespace_separator:
            self.itself = XML_ParserCreateNS(self.encoding, namespace_separator)
        else:
            self.itself = XML_ParserCreate(self.encoding)

        self.buffer_w = None
        self.buffer_size = 8192
        self.w_character_data_handler = None

        self._exc_info = None

    # Handlers management

    def w_convert(self, space, s):
        if self.returns_unicode:
            return space.call_function(
                space.getattr(space.wrap(s), space.wrap("decode")),
                space.wrap(self.encoding),
                space.wrap("strict"))
        else:
            return space.wrap(s)

    def w_convert_charp(self, space, data):
        if data:
            return self.w_convert(space, rffi.charp2str(data))
        else:
            return space.w_None

    def w_convert_charp_n(self, space, data, length):
        if data:
            return self.w_convert(space, rffi.charp2strn(data, length))
        else:
            return space.w_None

    def w_convert_model(self, space, model):
        children = [self._conv_content_model(model.children[i])
                    for i in range(model.c_numchildren)]
        return space.newtuple([
            space.wrap(model.c_type),
            space.wrap(model.c_quant),
            self.w_convert_charp(space, model.c_name),
            space.newtuple(children)])

    def sethandler(self, space, name, w_handler):
        if name == 'StartElementHandler':
            def callback(unused, name, attrs):
                self.flush_character_buffer(space)
                w_name = self.w_convert_charp(space, name)

                if self.specified_attributes:
                    maxindex = XML_GetSpecifiedAttributeCount(self.itself)
                else:
                    maxindex = 0
                while attrs[maxindex]:
                    maxindex += 2 # copied

                if self.ordered_attributes:
                    w_attrs = space.newlist([
                        self.w_convert_charp(space, attrs[i])
                        for i in range(maxindex)])
                else:
                    w_attrs = space.newdict()
                    for i in range(0, maxindex, 2):
                        space.setitem(
                            w_attrs,
                            self.w_convert_charp(space, attrs[i]),
                            self.w_convert_charp(space, attrs[i + 1]))
                space.call_function(w_handler, w_name, w_attrs)

        elif name == 'CharacterDataHandler':
            def callback(unused, data, length):
                w_string = self.w_convert_charp_n(space, data, length)

                if self.buffer_w is None:
                    space.call_function(w_handler, w_string)
                else:
                    if len(self.buffer_w) + length > self.buffer_size: # XXX sum(len(buffer))
                        self.flush_character_buffer(space)
                        if self.w_character_data_handler is None:
                            return
                    if length >= self.buffer_size:
                        space.call_function(w_handler, w_string)
                        self.buffer_w = []
                    else:
                        self.buffer_w.append(w_string)
            self.flush_character_buffer(space)
            if space.is_w(w_handler, space.w_None):
                self.w_character_data_handler = None
            else:
                self.w_character_data_handler = w_handler

        elif name in ['DefaultHandlerExpand', 'DefaultHandler']:
            def callback(unused, data, length):
                w_string = self.w_convert_charp_n(space, data, length)
                space.call_function(w_handler, w_string)

        elif name == 'ElementDeclHandler':
            def callback(unused, name, model):
                self.flush_character_buffer(space)
                w_model = self.w_convert_model(space, model)
                XML_FreeContentModel(self.itself, model)
                space.call_function(w_handler,
                                    self.w_convert_charp(space, name),
                                    w_model)

        elif name == 'EntityDeclHandler':
            def callback(unused, ename, is_param, value, value_len,
                         base, system_id, pub_id, not_name):
                self.flush_character_buffer(space)

                space.call_function(
                    w_handler,
                    self.w_convert_charp(space, ename),
                    space.wrap(is_param),
                    self.w_convert_charp_n(space, value, value_len),
                    self.w_convert_charp(space, base),
                    self.w_convert_charp(space, system_id),
                    self.w_convert_charp(space, pub_id),
                    self.w_convert_charp(space, not_name))

        elif name == 'ExternalEntityRefHandler':
            def callback(unused, context, base, system_id, pub_id):
                w_res = space.call_function(
                    w_handler,
                    self.w_convert_charp(space, context),
                    self.w_convert_charp(space, base),
                    self.w_convert_charp(space, system_id),
                    self.w_convert_charp(space, pub_id))
                if space.is_w(w_res, space.w_None):
                    return 0
                return space.int_w(w_res)

        else:
            ARGTYPES = HANDLERS[name]
            def callback(unused, *args):
                self.flush_character_buffer(space)
                args_w = []
                for i, arg in enumerate(args):
                    if ARGTYPES[i] is rffi.CCHARP:
                        w_arg = self.w_convert_charp(space, arg)
                    else:
                        w_arg = space.wrap(arg)
                    args_w.append(w_arg)
                space.call_function(w_handler, *args_w)

        def callback_wrapper(*args):
            # Catch errors and record them
            try:
                return callback(*args)
            except OperationError, e:
                self._exc_info = e
                XML_StopParser(self.itself, XML_FALSE)
        callback_wrapper.func_name = name + '_callback'
        SETTERS[name](self.itself, callback_wrapper)

    def setattr(self, space, name, w_value):
        if name == "namespace_prefixes":
            XML_SetReturnNSTriplet(self.itself, space.int_w(w_value))
            return
        elif name in SETTERS:
            return self.sethandler(space, name, w_value)

        # fallback to object.__setattr__()
        return space.call_function(
            object_setattr(space),
            space.wrap(self), space.wrap(name), w_value)
    setattr.unwrap_spec = ['self', ObjSpace, str, W_Root]

    # Parse methods

    def Parse(self, space, data, isfinal=True):
        res = XML_Parse(self.itself, data, len(data), isfinal)
        if self._exc_info:
            e = self._exc_info
            self._exc_info = None
            raise e
        elif res == 0:
            exc = self.set_error(space, XML_GetErrorCode(self.itself))
            raise exc
        self.flush_character_buffer(space)
        return res
    Parse.unwrap_spec = ['self', ObjSpace, str, bool]

    def ParseFile(self, space, w_file):
        return
    ParseFile.unwrap_spec = ['self', ObjSpace, W_Root]

    def flush_character_buffer(self, space):
        if not self.buffer_w:
            return
        w_data = space.call_function(
            space.getattr(space.wrap(''), space.wrap('join')),
            space.newlist(self.buffer_w))
        self.buffer_w = []

        if self.w_character_data_handler:
            space.call_function(self.w_character_data_handler, w_data)

    # Error management

    def set_error(self, space, code):
        err = rffi.charp2strn(XML_ErrorString(code), 200)
        lineno = XML_GetCurrentLineNumber(self.itself)
        colno = XML_GetCurrentColumnNumber(self.itself)
        msg = "%s: line: %d, column: %d" % (err, lineno, colno)
        w_module = space.getbuiltinmodule('pyexpat')
        w_errorcls = space.getattr(w_module, space.wrap('error'))
        w_error = space.call_function(
            w_errorcls,
            space.wrap(msg), space.wrap(code),
            space.wrap(colno), space.wrap(lineno))
        self.w_error = w_error
        return OperationError(w_errorcls, w_error)

    def descr_ErrorCode(space, self):
        return space.wrap(XML_GetErrorCode(self.itself))

    def descr_ErrorLineNumber(space, self):
        return space.wrap(XML_GetErrorLineNumber(self.itself))

    def descr_ErrorColumnNumber(space, self):
        return space.wrap(XML_GetErrorColumnNumber(self.itself))

    def descr_ErrorByteIndex(space, self):
        return space.wrap(XML_GetErrorByteIndex(self.itself))

    def get_buffer_text(space, self):
        return space.wrap(self.buffer_w is not None)
    def set_buffer_text(space, self, w_value):
        if space.is_true(w_value):
            self.buffer_w = []
        else:
            self.flush_character_buffer(space)
            self.buffer_w = None

    def get_intern(space, self):
        return self.w_intern


def bool_property(name, cls, doc=None):
    def fget(space, obj):
        return space.wrap(getattr(obj, name))
    def fset(space, obj, value):
        setattr(obj, name, space.bool_w(value))
    return GetSetProperty(fget, fset, cls=cls, doc=doc)

W_XMLParserType.typedef = TypeDef(
    "pyexpat.XMLParserType",
    __doc__ = "XML parser",
    __setattr__ = interp2app(W_XMLParserType.setattr),
    returns_unicode = bool_property('returns_unicode', W_XMLParserType),
    ordered_attributes = bool_property('ordered_attributes', W_XMLParserType),
    specified_attributes = bool_property('specified_attributes', W_XMLParserType),
    intern = GetSetProperty(W_XMLParserType.get_intern, cls=W_XMLParserType),
    buffer_text = GetSetProperty(W_XMLParserType.get_buffer_text,
                                 W_XMLParserType.set_buffer_text, cls=W_XMLParserType),

    ErrorCode = GetSetProperty(W_XMLParserType.descr_ErrorCode, cls=W_XMLParserType),
    ErrorLineNumber = GetSetProperty(W_XMLParserType.descr_ErrorLineNumber, cls=W_XMLParserType),
    ErrorColumnNumber = GetSetProperty(W_XMLParserType.descr_ErrorColumnNumber, cls=W_XMLParserType),
    ErrorByteIndex = GetSetProperty(W_XMLParserType.descr_ErrorByteIndex, cls=W_XMLParserType),
    CurrentLineNumber = GetSetProperty(W_XMLParserType.descr_ErrorLineNumber, cls=W_XMLParserType),
    CurrentColumnNumber = GetSetProperty(W_XMLParserType.descr_ErrorColumnNumber, cls=W_XMLParserType),
    CurrentByteIndex = GetSetProperty(W_XMLParserType.descr_ErrorByteIndex, cls=W_XMLParserType),

    **dict((name, interp2app(getattr(W_XMLParserType, name),
                             unwrap_spec=getattr(W_XMLParserType,
                                                 name).unwrap_spec))
           for name in "Parse ParseFile".split())
    )

def ParserCreate(space, w_encoding=None, w_namespace_separator=None,
                 w_intern=NoneNotWrapped):
    if space.is_w(w_encoding, space.w_None):
        encoding = None
    else:
        encoding = space.str_w(w_encoding)

    if space.is_w(w_namespace_separator, space.w_None):
        namespace_separator = '\0'
    else:
        separator = space.str_w(w_namespace_separator)
        if len(separator) == 0:
            namespace_separator = '\0'
        elif len(separator) == 1:
            namespace_separator = separator[0]
        else:
            raise OperationError(
                space.w_ValueError,
                space.wrap('namespace_separator must be at most one character,'
                           ' omitted, or None'))
    if w_intern is None:
        w_intern = space.newdict()

    parser = W_XMLParserType(encoding, namespace_separator, w_intern)
    return space.wrap(parser)
ParserCreate.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root]

def ErrorString(space, code):
    return space.wrap(rffi.charp2str(XML_ErrorString(code)))
ErrorString.unwrap_spec = [ObjSpace, int]

