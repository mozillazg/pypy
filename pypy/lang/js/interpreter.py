
import math
from pypy.lang.js.jsparser import parse, ParseError
from pypy.lang.js.astbuilder import ASTBuilder
from pypy.lang.js.jsobj import global_context, W_Object,\
     w_Undefined, W_NewBuiltin, W_IntNumber, w_Null, create_object, W_Boolean,\
     W_FloatNumber, W_String, W_Builtin, W_Array, w_Null, newbool,\
     isnull_or_undefined, W_PrimitiveObject, W_ListObject, W_BaseNumber,\
     DE, DD, RO, IT
from pypy.lang.js.execution import ThrowException, JsTypeError
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.streamio import open_file_as_stream
from pypy.lang.js.jscode import JsCode
from pypy.rlib.rarithmetic import NAN, INFINITY, isnan, isinf, r_uint
from pypy.rlib.objectmodel import specialize

ASTBUILDER = ASTBuilder()

def writer(x):
    print x

def load_source(script_source, sourcename):
    temp_tree = parse(script_source)
    ASTBUILDER.sourcename = sourcename
    return ASTBUILDER.dispatch(temp_tree)

def load_file(filename):
    f = open_file_as_stream(filename)
    t = load_source(f.readall(), filename)
    f.close()
    return t

class W_NativeObject(W_Object):
    def __init__(self, Class, Prototype, ctx=None,
                 Value=w_Undefined, callfunc=None):
        W_Object.__init__(self, ctx, Prototype,
                          Class, Value, callfunc)
    
class W_ObjectObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            return args[0].ToObject(ctx)
        else:
            return self.Construct(ctx)

    def Construct(self, ctx, args=[]):
        if (len(args) >= 1 and not args[0] is w_Undefined and not
            args[0] is w_Null):
            # XXX later we could separate builtins and normal objects
            return args[0].ToObject(ctx)
        return create_object(ctx, u'Object')

class W_BooleanObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            return newbool(args[0].ToBoolean())
        else:
            return newbool(False)

    def Construct(self, ctx, args=[]):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            Value = newbool(args[0].ToBoolean())
            return create_object(ctx, u'Boolean', Value = Value)
        return create_object(ctx, u'Boolean', Value = newbool(False))

class W_NumberObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            return W_FloatNumber(args[0].ToNumber(ctx))
        elif len(args) >= 1 and args[0] is w_Undefined:
            return W_FloatNumber(NAN)
        else:
            return W_FloatNumber(0.0)

    def ToNumber(self, ctx):
        return 0.0

    def Construct(self, ctx, args=[]):
        if len(args) >= 1 and not isnull_or_undefined(args[0]):
            Value = W_FloatNumber(args[0].ToNumber(ctx))
            return create_object(ctx, u'Number', Value = Value)
        return create_object(ctx, u'Number', Value = W_FloatNumber(0.0))

class W_StringObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1:
            return W_String(args[0].ToString(ctx))
        else:
            return W_String(u'')

    def Construct(self, ctx, args=[]):
        if len(args) >= 1:
            Value = W_String(args[0].ToString(ctx))
            return Value.ToObject(ctx)
        return W_String(u'').ToObject(ctx)

def create_array(ctx, elements=[]):
    proto = ctx.get_global().Get(ctx, u'Array').Get(ctx, u'prototype')
    array = W_Array(ctx, Prototype=proto, Class = proto.Class)
    i = 0
    while i < len(elements):
        array.Put(ctx, unicode(str(i)), elements[i])
        i += 1
    
    return array

class W_ArrayObject(W_NativeObject):
    def Call(self, ctx, args=[], this=None):
        if len(args) == 1 and isinstance(args[0], W_BaseNumber):
            array = create_array(ctx)
            array.Put(ctx, u'length', args[0])
        else:
            array = create_array(ctx, args)
        return array

    def Construct(self, ctx, args=[]):
        return self.Call(ctx, args)

TEST = False

def evaljs(ctx, args, this):
    if len(args) >= 1:
        if  isinstance(args[0], W_String):
            src = args[0].ToString(ctx).encode('ascii') # XXX what is the best aproach here?
        else:
            return args[0]
    else:
        src = ''
    try:
        node = load_source(src, 'evalcode')
    except ParseError, e:
        raise ThrowException(W_String(u'SyntaxError: ' + unicode(str(e))))

    bytecode = JsCode()
    node.emit(bytecode)
    return bytecode.run(ctx, retlast=True)

def parseIntjs(ctx, args, this):
    if len(args) < 1:
        return W_FloatNumber(NAN)
    s = args[0].ToString(ctx).strip(u' ')
    if len(args) > 1:
        radix = args[1].ToInt32(ctx)
    else:
        radix = 10
    if len(s) >= 2 and (s.startswith(u'0x') or s.startswith(u'0X')) :
        radix = 16
        s = s[2:]
    if s == u'' or radix < 2 or radix > 36:
        return W_FloatNumber(NAN)
    try:
        n = int(s.encode('ascii'), radix)
    except ValueError:
        return W_FloatNumber(NAN)
    return W_IntNumber(n)

def parseFloatjs(ctx, args, this):
    if len(args) < 1:
        return W_FloatNumber(NAN)
    s = args[0].ToString(ctx).strip(u' ')
    try:
        n = float(s.encode('ascii'))
    except ValueError:
        n = NAN
    return W_FloatNumber(n)
    

def printjs(ctx, args, this):
    writer(u','.join([i.ToString(ctx) for i in args]))
    return w_Undefined

def isnanjs(ctx, args, this):
    if len(args) < 1:
        return newbool(True)
    return newbool(isnan(args[0].ToNumber(ctx)))

def isfinitejs(ctx, args, this):
    if len(args) < 1:
        return newbool(True)
    n = args[0].ToNumber(ctx)
    if  isinf(n) or isnan(n):
        return newbool(False)
    else:
        return newbool(True)
        
def absjs(ctx, args, this):
    val = args[0]
    if isinstance(val, W_IntNumber):
        if val.intval > 0:
            return val # fast path
        return W_IntNumber(-val.intval)
    return W_FloatNumber(abs(args[0].ToNumber(ctx)))

def floorjs(ctx, args, this):
    return W_IntNumber(int(math.floor(args[0].ToNumber(ctx))))

def powjs(ctx, args, this):
    return W_FloatNumber(math.pow(args[0].ToNumber(ctx), args[1].ToNumber(ctx)))

def sqrtjs(ctx, args, this):
    return W_FloatNumber(math.sqrt(args[0].ToNumber(ctx)))

def versionjs(ctx, args, this):
    return w_Undefined

def _ishex(ch):
    return ((ch >= u'a' and ch <= u'f') or (ch >= u'0' and ch <= u'9') or
            (ch >= u'A' and ch <= u'F'))

def unescapejs(ctx, args, this):
    # XXX consider using StringBuilder here
    res = []
    if not isinstance(args[0], W_String):
        raise JsTypeError(W_String(u'Expected string'))
    strval = args[0].strval
    lgt = len(strval)
    i = 0
    while i < lgt:
        ch = strval[i]
        if ch == u'%':
            if (i + 2 < lgt and _ishex(strval[i+1]) and _ishex(strval[i+2])):
                ch = unichr(int((strval[i + 1] + strval[i + 2]).encode('ascii'), 16))
                i += 2
            elif (i + 5 < lgt and strval[i + 1] == 'u' and
                  _ishex(strval[i + 2]) and _ishex(strval[i + 3]) and
                  _ishex(strval[i + 4]) and _ishex(strval[i + 5])):
                ch = unichr(int((strval[i+2:i+6]).encode('ascii'), 16))
                i += 5
        i += 1
        res.append(ch)
    return W_String(u''.join(res))

class W_ToString(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        return W_String(u'[object ' + this.Class + u']')

class W_ValueOf(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        return this

class W_HasOwnProperty(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1:
            propname = args[0].ToString(ctx)
            if propname in this.propdict:
                return newbool(True)
        return newbool(False)

class W_IsPrototypeOf(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and isinstance(args[0], W_PrimitiveObject):
            O = this
            V = args[0].Prototype
            while V is not None:
                if O == V:
                    return newbool(True)
                V = V.Prototype
        return newbool(False)

class W_PropertyIsEnumerable(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1:
            propname = args[0].ToString(ctx)
            if propname in this.propdict and not this.propdict[propname].flags & DE:
                return newbool(True)
        return newbool(False)

class W_Function(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        tam = len(args)
        if tam >= 1:
            fbody  = args[tam-1].ToString(ctx)
            argslist = []
            for i in range(tam-1):
                argslist.append(args[i].ToString(ctx))
            fargs = u','.join(argslist)
            functioncode = u'function (' + fargs + u') {' + fbody + u'}'
        else:
            functioncode = u'function () {}'
        
        functioncode = unicode(functioncode).encode('ascii') # XXX this is potentialy very bad
        #remove program and sourcelements node
        funcnode = parse(functioncode).children[0].children[0]
        ast = ASTBUILDER.dispatch(funcnode)
        bytecode = JsCode()
        ast.emit(bytecode)
        return bytecode.run(ctx, retlast=True)
    
    def Construct(self, ctx, args=[]):
        return self.Call(ctx, args, this=None)

functionstring= u'function (arguments go here!) {\n'+ \
                u'    [lots of stuff :)]\n'+ \
                u'}'
class W_FToString(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if this.Class == u'Function':
            return W_String(functionstring)
        else:
            raise JsTypeError(u'this is not a function object')

class W_Apply(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        try:
            if isnull_or_undefined(args[0]):
                thisArg = ctx.get_global()
            else:
                thisArg = args[0].ToObject(ctx)
        except IndexError:
            thisArg = ctx.get_global()
        
        try:
            arrayArgs = args[1]
            if isinstance(arrayArgs, W_ListObject):
                callargs = arrayArgs.tolist()
            elif isnull_or_undefined(arrayArgs):
                callargs = []
            else:
                raise JsTypeError(u'arrayArgs is not an Array or Arguments object')
        except IndexError:
            callargs = []
        return this.Call(ctx, callargs, this=thisArg)

class W_Call(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1:
            if isnull_or_undefined(args[0]):
                thisArg = ctx.get_global()
            else:
                thisArg = args[0]
            callargs = args[1:]
        else:
            thisArg = ctx.get_global()
            callargs = []
        return this.Call(ctx, callargs, this = thisArg)

class W_ValueToString(W_NewBuiltin):
    "this is the toString function for objects with Value"
    mytype = u''
    def Call(self, ctx, args=[], this=None):
        if this.Value.type() != self.mytype:
            raise JsTypeError(u'Wrong type')
        return W_String(this.Value.ToString(ctx))


class W_NumberValueToString(W_ValueToString):
    mytype = u'number'

class W_BooleanValueToString(W_ValueToString):
    mytype = u'boolean'

class W_StringValueToString(W_ValueToString):
    mytype = u'string'


@specialize.memo()
def get_value_of(type):
    class W_ValueValueOf(W_NewBuiltin):
        "this is the valueOf function for objects with Value"
        def Call(self, ctx, args=[], this=None):
            if type != this.Class:
                raise JsTypeError(self.type() + u'.prototype.valueOf called with incompatible type')
            return this.Value
    return W_ValueValueOf

class W_FromCharCode(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        temp = []
        for arg in args:
            i = arg.ToInt32(ctx) % 65536 # XXX should be uint16
            temp.append(unichr(i))
        
        return W_String(u''.join(temp))

class W_ToLower(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        if we_are_translated():
            temp = string.encode('ascii')
            return W_String(unicode(temp.lower())) # XXX rpython unicode doesn't have lower
        else:
            return W_String(string.lower())

class W_ToUpper(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        if we_are_translated():
            temp = string.encode('ascii')
            return W_String(unicode(temp.upper())) # XXX rpython unicode doesn't have upper
        else:
            return W_String(string.upper())

class W_CharAt(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        if len(args)>=1:
            pos = args[0].ToInt32(ctx)
            if (not pos >=0) or (pos > len(string) - 1):
                return W_String(u'')
        else:
            return W_String(u'')
        return W_String(string[pos])

class W_CharCodeAt(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        if len(args)>=1:
            pos = args[0].ToInt32(ctx)
            if (not pos >=0) or (pos > len(string) - 1):
                return W_String(u'')
        else:
            return W_String(u'')
        return W_IntNumber(ord(string[pos]))

class W_Concat(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        others = [obj.ToString(ctx) for obj in args]
        string += u''.join(others)
        return W_String(string)

class W_IndexOf(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        if len(args) < 1:
            return W_IntNumber(-1)
        substr = args[0].ToString(ctx)
        size = len(string)
        subsize = len(substr)
        if len(args) < 2:
            pos = 0
        else:
            pos = args[1].ToInt32(ctx)
        pos = min(max(pos, 0), size)
        return W_IntNumber(string.find(substr, pos))

class W_Substring(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        size = len(string)
        if len(args) < 1:
            start = 0
        else:
            start = args[0].ToInt32(ctx)
        if len(args) < 2:
            end = size
        else:
            end = args[1].ToInt32(ctx)
        tmp1 = min(max(start, 0), size)
        tmp2 = min(max(end, 0), size)
        start = min(tmp1, tmp2)
        end = max(tmp1, tmp2)
        return W_String(string[start:end])

class W_Split(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        string = this.ToString(ctx)
        
        if len(args) < 1 or args[0] is w_Undefined:
            return create_array(ctx, [W_String(string)])
        else:
            separator = args[0].ToString(ctx)
        
        if len(args) >= 2:
            #limit = args[1].ToUInt32(ctx)
            raise ThrowException(W_String(u'limit not implemented'))
            # array = string.split(separator, limit)
        else:
            if we_are_translated():
                temp = string.encode('ascii')
                tempsep = separator.encode('ascii')
                arrtemp = temp.split(tempsep)
                array = []
                for i in arrtemp:
                    array.append(unicode(i))
            else:
                array = string.split(separator)
        
        w_array = create_array(ctx)
        i = 0
        while i < len(array):
            w_str = W_String(array[i])
            w_array.Put(ctx, unicode(str(i)), w_str)
            i += 1
        
        return w_array


def common_join(ctx, this, sep=u','):
    length = this.Get(ctx, u'length').ToUInt32(ctx)
    l = []
    i = 0
    while i < length:
        item = this.Get(ctx, unicode(str(i)))
        if isnull_or_undefined(item):
            item_string = u''
        else:
            item_string = item.ToString(ctx)
        l.append(item_string)
        i += 1
        
    return sep.join(l)

class W_ArrayToString(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        return W_String(common_join(ctx, this, sep=u','))

class W_ArrayJoin(W_NewBuiltin):
    def Call(self, ctx, args=[], this=None):
        if len(args) >= 1 and not args[0] is w_Undefined:
            sep = args[0].ToString(ctx)
        else:
            sep = u','
        
        return W_String(common_join(ctx, this, sep))

class W_ArrayReverse(W_NewBuiltin):
    length = 0
    def Call(self, ctx, args=[], this=None):
        r2 = this.Get(ctx, u'length').ToUInt32(ctx)
        k = r_uint(0)
        r3 = r_uint(math.floor( float(r2)/2.0 ))
        if r3 == k:
            return this
        
        while k < r3:
            r6 = r2 - k - 1
            r7 = unicode(str(k))
            r8 = unicode(str(r6))
            
            r9 = this.Get(ctx, r7)
            r10 = this.Get(ctx, r8)
            
            this.Put(ctx, r7, r10)
            this.Put(ctx, r8, r9)
            k += 1
        
        return this

class W_DateFake(W_NewBuiltin): # XXX This is temporary
    def Call(self, ctx, args=[], this=None):
        return create_object(ctx, u'Object')
    
    def Construct(self, ctx, args=[]):
        return create_object(ctx, u'Object')

def pypy_repr(ctx, repr, w_arg):
    return W_String(w_arg.__class__.__name__)

def put_values(ctx, obj, dictvalues):
    for key,value in dictvalues.iteritems():
        obj.Put(ctx, key, value)

class Interpreter(object):
    """Creates a js interpreter"""
    def __init__(self):        
        allon = DE | DD | RO
        w_Global = W_Object(Class=u'global')
        
        ctx = global_context(w_Global)
        
        w_ObjPrototype = W_Object(Prototype=None, Class=u'Object')
        
        w_Function = W_Function(ctx, Class=u'Function', 
                              Prototype=w_ObjPrototype)
        w_Function.Put(ctx, u'length', W_IntNumber(1), flags = allon)
        w_Global.Put(ctx, u'Function', w_Function)
        
        w_Object = W_ObjectObject(u'Object', w_Function)
        w_Object.Put(ctx, u'prototype', w_ObjPrototype, flags = allon)
        w_Object.Put(ctx, u'length', W_IntNumber(1), flags = RO | DD)
        w_Global.Put(ctx, u'Object', w_Object)
        w_Global.Prototype = w_ObjPrototype
        
        w_FncPrototype = w_Function.Call(ctx, this=w_Function)
        w_Function.Put(ctx, u'prototype', w_FncPrototype, flags = allon)
        w_Function.Put(ctx, u'constructor', w_Function)
        
        toString = W_ToString(ctx)
        
        put_values(ctx, w_ObjPrototype, {
            u'constructor': w_Object,
            u'__proto__': w_FncPrototype,
            u'toString': toString,
            u'toLocaleString': toString,
            u'valueOf': W_ValueOf(ctx),
            u'hasOwnProperty': W_HasOwnProperty(ctx),
            u'isPrototypeOf': W_IsPrototypeOf(ctx),
            u'propertyIsEnumerable': W_PropertyIsEnumerable(ctx),
        })
        
        #properties of the function prototype
        put_values(ctx, w_FncPrototype, {
            u'constructor': w_Function,
            u'__proto__': w_FncPrototype,
            u'toString': W_FToString(ctx),
            u'apply': W_Apply(ctx),
            u'call': W_Call(ctx),
            u'arguments': w_Null,
        })
        
        w_Boolean = W_BooleanObject(u'Boolean', w_FncPrototype)
        w_Boolean.Put(ctx, u'constructor', w_FncPrototype, flags = allon)
        w_Boolean.Put(ctx, u'length', W_IntNumber(1), flags = allon)
        
        w_BoolPrototype = create_object(ctx, u'Object', Value=newbool(False))
        w_BoolPrototype.Class = u'Boolean'
        
        put_values(ctx, w_BoolPrototype, {
            u'constructor': w_FncPrototype,
            u'__proto__': w_ObjPrototype,
            u'toString': W_BooleanValueToString(ctx),
            u'valueOf': get_value_of(u'Boolean')(ctx),
        })

        w_Boolean.Put(ctx, u'prototype', w_BoolPrototype, flags = allon)
        w_Global.Put(ctx, u'Boolean', w_Boolean)

        #Number
        w_Number = W_NumberObject(u'Number', w_FncPrototype)

        w_empty_fun = w_Function.Call(ctx, args=[W_String(u'')])

        w_NumPrototype = create_object(ctx, u'Object', Value=W_FloatNumber(0.0))
        w_NumPrototype.Class = u'Number'
        put_values(ctx, w_NumPrototype, {
            u'constructor': w_Number,
            u'__proto__': w_empty_fun,
            u'toString': W_NumberValueToString(ctx),
            u'valueOf': get_value_of(u'Number')(ctx),
        })

        put_values(ctx, w_Number, {
            u'constructor': w_FncPrototype,
            u'prototype': w_NumPrototype,
            u'__proto__': w_empty_fun,
            u'length'   : W_IntNumber(1),
        })
        w_Number.propdict[u'prototype'].flags |= RO
        w_Number.Put(ctx, u'MAX_VALUE', W_FloatNumber(1.7976931348623157e308), flags = RO|DD)
        w_Number.Put(ctx, u'MIN_VALUE', W_FloatNumber(0.0), flags = RO|DD)
        w_Number.Put(ctx, u'NaN', W_FloatNumber(NAN), flags = RO|DD)
        # ^^^ this is exactly in test case suite
        w_Number.Put(ctx, u'POSITIVE_INFINITY', W_FloatNumber(INFINITY), flags = RO|DD)
        w_Number.Put(ctx, u'NEGATIVE_INFINITY', W_FloatNumber(-INFINITY), flags = RO|DD)
        

        w_Global.Put(ctx, u'Number', w_Number)
        
                
        #String
        w_String = W_StringObject(u'String', w_FncPrototype)

        w_StrPrototype = create_object(ctx, u'Object', Value=W_String(u''))
        w_StrPrototype.Class = u'String'
        
        put_values(ctx, w_StrPrototype, {
            u'constructor': w_FncPrototype,
            u'__proto__': w_StrPrototype,
            u'toString': W_StringValueToString(ctx),
            u'valueOf': get_value_of(u'String')(ctx),
            u'toLowerCase': W_ToLower(ctx),
            u'toUpperCase': W_ToUpper(ctx),
            u'charAt': W_CharAt(ctx),
            u'charCodeAt': W_CharCodeAt(ctx),
            u'concat': W_Concat(ctx),
            u'indexOf': W_IndexOf(ctx),
            u'substring': W_Substring(ctx),
            u'split': W_Split(ctx),
        })
        
        w_String.Put(ctx, u'prototype', w_StrPrototype)
        w_String.Put(ctx, u'fromCharCode', W_FromCharCode(ctx))
        w_Global.Put(ctx, u'String', w_String)

        w_Array = W_ArrayObject(u'Array', w_FncPrototype)

        w_ArrPrototype = W_Array(Prototype=w_ObjPrototype)
        w_arr_join = W_ArrayJoin(ctx)
        w_arr_join.Put(ctx, u'length', W_IntNumber(1), flags=allon)
        
        put_values(ctx, w_ArrPrototype, {
            u'constructor': w_FncPrototype,
            u'__proto__': w_ArrPrototype,
            u'toString': W_ArrayToString(ctx),
            u'join': w_arr_join,
            u'reverse': W_ArrayReverse(ctx),
        })
        
        w_Array.Put(ctx, u'prototype', w_ArrPrototype, flags = allon)
        w_Array.Put(ctx, u'__proto__', w_FncPrototype, flags = allon)
        w_Array.Put(ctx, u'length', W_IntNumber(1), flags = allon)
        w_Global.Put(ctx, u'Array', w_Array)
        
        
        #Math
        w_math = W_Object(Class=u'Math')
        w_Global.Put(ctx, u'Math', w_math)
        w_math.Put(ctx, u'__proto__',  w_ObjPrototype)
        w_math.Put(ctx, u'prototype', w_ObjPrototype, flags = allon)
        w_math.Put(ctx, u'abs', W_Builtin(absjs, Class=u'function'))
        w_math.Put(ctx, u'floor', W_Builtin(floorjs, Class=u'function'))
        w_math.Put(ctx, u'pow', W_Builtin(powjs, Class=u'function'))
        w_math.Put(ctx, u'sqrt', W_Builtin(sqrtjs, Class=u'function'))
        w_math.Put(ctx, u'E', W_FloatNumber(math.e))
        w_math.Put(ctx, u'PI', W_FloatNumber(math.pi))
        
        w_Global.Put(ctx, u'version', W_Builtin(versionjs))
        
        #Date
        w_Date = W_DateFake(ctx, Class=u'Date')
        w_Global.Put(ctx, u'Date', w_Date)
        
        w_Global.Put(ctx, u'NaN', W_FloatNumber(NAN), flags = DE|DD)
        w_Global.Put(ctx, u'Infinity', W_FloatNumber(INFINITY), flags = DE|DD)
        w_Global.Put(ctx, u'undefined', w_Undefined, flags = DE|DD)        
        w_Global.Put(ctx, u'eval', W_Builtin(evaljs))
        w_Global.Put(ctx, u'parseInt', W_Builtin(parseIntjs))
        w_Global.Put(ctx, u'parseFloat', W_Builtin(parseFloatjs))
        w_Global.Put(ctx, u'isNaN', W_Builtin(isnanjs))
        w_Global.Put(ctx, u'isFinite', W_Builtin(isfinitejs))            
        w_Global.Put(ctx, u'print', W_Builtin(printjs))
        w_Global.Put(ctx, u'unescape', W_Builtin(unescapejs))

        w_Global.Put(ctx, u'this', w_Global)

        # DEBUGGING
        if 0:
            w_Global.Put(ctx, u'pypy_repr', W_Builtin(pypy_repr))
        
        self.global_context = ctx
        self.w_Global = w_Global
        self.w_Object = w_Object

    def run(self, script, interactive=False):
        """run the interpreter"""
        bytecode = JsCode()
        script.emit(bytecode)
        if not we_are_translated():
            # debugging
            self._code = bytecode
        if interactive:
            return bytecode.run(self.global_context, retlast=True)
        else:
            bytecode.run(self.global_context)
