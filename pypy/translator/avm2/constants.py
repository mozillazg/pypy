
import struct
from pypy.translator.avm2.util import serialize_u32 as u32, ValuePool

# ======================================
# Constants
# ======================================

# ======================================
# Method Flags
# ======================================

"""
Suggest to the run-time that an arguments object (as specified by
the ActionScript 3.0 Language Reference) be created. Must not be used
together with METHODFLAG_NeedRest
"""
METHODFLAG_Arguments     = 0x01

"""
Must be set if this method uses the newactivation opcode
"""
METHODFLAG_Activation    = 0x02

"""
This flag creates an ActionScript 3.0 ...rest arguments array.
Must not by used with METHODFLAG_Arguments
"""
METHODFLAG_NeedRest      = 0x04

"""
Must be set if this method has optional parameters and the options
field is present in this method_info structure.
"""
METHODFLAG_HasOptional   = 0x08

"""
Undocumented as of now.
"""
METHODFLAG_IgnoreRest    = 0x10

"""
Undocumented as fo now. Assuming this flag is to implement the
"native" keyword in AS3.
"""
METHODFLAG_Native        = 0x20

"""
Must be set if this method uses the dxns or dxnslate opcodes.
"""

METHODFLAG_SetsDxns      = 0x40

"""
Must be set when the param_names field is presetn in this method_info
structure.
"""
METHODFLAG_HasParamNames = 0x80

# ======================================
# Types
# ======================================

# String types
TYPE_STRING_Utf8                  = 0x01

# Number types
TYPE_NUMBER_Int                   = 0x03
TYPE_NUMBER_UInt                  = 0x04
TYPE_NUMBER_DOUBLE                = 0x06

# Boolean types
TYPE_BOOLEAN_False                = 0x0A
TYPE_BOOLEAN_True                 = 0x0B

# Object types
TYPE_OBJECT_Undefined             = 0x00
TYPE_OBJECT_Null                  = 0x0C

# Namespace types
TYPE_NAMESPACE_PrivateNamespace   = 0x05
TYPE_NAMESPACE_Namespace          = 0x08
TYPE_NAMESPACE_PackageNamespace   = 0x16
TYPE_NAMESPACE_PackageInternalNs  = 0x17
TYPE_NAMESPACE_ProtectedNamespace = 0x18
TYPE_NAMESPACE_ExplicitNamespace  = 0x19
TYPE_NAMESPACE_StaticProtectedNs  = 0x1A

# Namespace Set types
TYPE_NAMESPACE_SET_NamespaceSet   = 0x15

# Multiname types
TYPE_MULTINAME_QName              = 0x07 # o.ns::name   - fully resolved at compile-time
TYPE_MULTINAME_QNameA             = 0x0D # o.@ns::name
TYPE_MULTINAME_Multiname          = 0x09 # o.name       - uses an nsset to resolve at runtime
TYPE_MULTINAME_MultinameA         = 0x0E # o.@name
TYPE_MULTINAME_RtqName            = 0x0F # o.ns::name   - namespace on stack
TYPE_MULTINAME_RtqNameA           = 0x10 # o.@ns::name
TYPE_MULTINAME_RtqNameL           = 0x11 # o.ns::[name] - namespace and name on stack
TYPE_MULTINAME_RtqNameLA          = 0x12 # o.@ns::name
TYPE_MULTINAME_NameL              = 0x13 # o.[name]     - implied public namespace, name on stack
TYPE_MULTINAME_NameLA             = 0x14 # o.@[name]
TYPE_MULTINAME_MultinameL         = 0x1B # o.[name]     - 
TYPE_MULTINAME_MultinameLA        = 0x1C # o.@[name]
TYPE_MULTINAME_TypeName           = 0x1D # o.ns::name.<generic> - used to implement Vector

def py_to_abc(value, pool):
    if value is True:
        return TYPE_BOOLEAN_True, 0
    if value is False:
        return TYPE_BOOLEAN_False, 0
    if value is None:
        return TYPE_OBJECT_Null, 0
    if isinstance(value, basestring):
        return TYPE_STRING_Utf8
    if isinstance(value, int):
        if value < 0:
            return TYPE_NUMBER_Int, pool.int_pool.index_for(value)
        return TYPE_NUMBER_UInt, pool.uint_pool.index_for(value)
    if isinstance(value, float):
        return TYPE_NUMBER_DOUBLE, pool.double_pool.index_for(value)
    if isinstance(value, Namespace):
        return value.kind, pool.namespace_pool.index_for(value)
    if isinstance(value, NamespaceSet):
        return TYPE_NAMESPACE_SET_NamespaceSet, pool.nsset_pool.index_for(value)
    if hasattr(value, "multiname"):
        return value.multiname().KIND, pool.multiname_pool.index_for(value.multiname())
    raise ValueError, "This is not an ABC-compatible type."

# ======================================
# Namespaces
# ======================================

class Namespace(object):

    def __init__(self, kind, name):
        self.kind = kind
        self.name = name
        self._name_index = None

    def __hash__(self):
        return hash((self.name, self.kind))
        
    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name and self.kind == other.kind

    def __ne__(self, other):
        return not self == other
        
    def write_to_pool(self, pool):
        self._name_index = pool.utf8_pool.index_for(self.name)

    def serialize(self):
        assert self._name_index is not None, "Please call write_to_pool before serializing"
        return chr(self.kind) + u32(self._name_index)

class NamespaceSet(object):

    def __init__(self, *namespaces):
        self.namespaces = namespaces
        self._namespace_indices = None

    def __len__(self):
        return len(self.namespaces)

    def __hash__(self):
        return hash(tuple(self.namespaces))
    
    def __eq__(self, other):
        return  isinstance(other, self.__class__) and self.namespaces == other.namespaces

    def __ne__(self, other):
        return not self == other

    def write_to_pool(self, pool):
        self._namespace_indices = [pool.namespace_pool.index_for(ns) for ns in self.namespaces]
    
    def serialize(self):
        assert self._namespace_indices is not None, "Please call write_to_pool before serializing"
        return u32(len(self.namespaces)) + ''.join(u32(index) for index in self._namespace_indices)
        

NO_NAMESPACE  = Namespace(TYPE_NAMESPACE_Namespace, "")
ANY_NAMESPACE = Namespace(TYPE_NAMESPACE_Namespace, "*")

PACKAGE_NAMESPACE   = Namespace(TYPE_NAMESPACE_PackageNamespace, "")
PACKAGE_I_NAMESPACE = Namespace(TYPE_NAMESPACE_PackageInternalNs, "")
PRIVATE_NAMESPACE   = Namespace(TYPE_NAMESPACE_PrivateNamespace, "")
AS3_NAMESPACE       = Namespace(TYPE_NAMESPACE_Namespace, "http://adobe.com/AS3/2006/builtin")

NO_NAMESPACE_SET = NamespaceSet()
PROP_NAMESPACE_SET = NamespaceSet(PRIVATE_NAMESPACE, PACKAGE_NAMESPACE, PACKAGE_I_NAMESPACE, AS3_NAMESPACE)

ANY_NAME = object()

def packagedQName(ns, name):
    return QName(name, Namespace(TYPE_NAMESPACE_PackageNamespace, ns))

# ======================================
# Multinames
# ======================================

class MultinameL(object):
    KIND = TYPE_MULTINAME_MultinameL
    
    def __init__(self, ns_set):
        self.ns_set = ns_set
        self._ns_set_index = None

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.KIND == other.KIND and self.ns_set == other.ns_set

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.KIND, self.ns_set))
    
    def write_to_pool(self, pool):
        self._ns_set_index = pool.nsset_pool.index_for(self.ns_set)

    def serialize(self):
        assert self._ns_set_index is not None, "Please call write_to_pool before serializing"
        return chr(self.KIND) + u32(self._ns_set_index)

    def multiname(self):
        return self

class MultinameLA(MultinameL):
    KIND = TYPE_MULTINAME_MultinameLA

class Multiname(MultinameL):
    KIND = TYPE_MULTINAME_Multiname
    
    def __init__(self, name, ns_set):
        super(Multiname, self).__init__(ns_set)
        self.name = name
        self._name_index = None

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.KIND == other.KIND and self.name == other.name

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.KIND, self.name))

    def write_to_pool(self, pool):
        super(Multiname, self).write_to_pool(pool)
        assert self.name != ""
        if self.name == "*":
            self._name_index = 0
        else:
            self._name_index = pool.utf8_pool.index_for(self.name)

    def serialize(self):
        assert self._name_index is not None, "Please call write_to_pool before serializing"
        assert self._ns_set_index is not None, "Please call write_to_pool before serializing"
        return chr(self.KIND) + u32(self._name_index) + u32(self._ns_set_index)

class MultinameA(Multiname):
    KIND = TYPE_MULTINAME_MultinameA


class QName(object):
    KIND = TYPE_MULTINAME_QName
    
    def __init__(self, name, ns=None):
        self.name = name
        self.ns = ns or PACKAGE_NAMESPACE

        self._name_index = None
        self._ns_index = None

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.KIND == other.KIND and self.name == other.name and self.ns == other.ns

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.KIND, self.name, self.ns))
    
    def write_to_pool(self, pool):
        assert self.name != ""
        if self.name == "*":
            self._name_index = 0
        else:
            self._name_index = pool.utf8_pool.index_for(self.name)
        self._ns_index = pool.namespace_pool.index_for(self.ns)
        
    def serialize(self):
        assert self._name_index is not None, "Please call write_to_pool before serializing"
        assert self._ns_index is not None, "Please call write_to_pool before serializing"
        return chr(self.KIND) + u32(self._ns_index) + u32(self._name_index)

    def multiname(self):
        return self

class QNameA(QName):
    KIND = TYPE_MULTINAME_QNameA
    
class RtqNameL(object):
    KIND = TYPE_MULTINAME_RtqNameL
    
    def serialize(self):
        return chr(self.KIND)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.KIND == other.KIND

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.KIND))

class RtqNameLA(RtqNameL):
    KIND = TYPE_MULTINAME_RtqNameLA

class RtqName(object):
    KIND = TYPE_MULTINAME_RtqName

    def __init__(self, name):
        self.name = name
        self._name_index = None

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.KIND == other.KIND and self.name == other.name

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.KIND, self.name))
    
    def write_to_pool(self, pool):
        assert self.name != ""
        # if self.name == "*":
        #     self._name_index = 0
        # else:
        self._name_index = pool.utf8_pool.index_for(self.name)

    def serialize(self):
        assert self._name_index is not None, "Please call write_to_pool before serializing"
        return chr(self.KIND) + u32(self._name_index)

    def multiname(self):
        return self

class RtqNameA(RtqName):
    KIND = TYPE_MULTINAME_RtqNameA

class TypeName(object):
    KIND = TYPE_MULTINAME_TypeName

    def __init__(self, name, *types):
        self.name  = name
        self.types = list(types)
        
        self._name_index = None
        self._types_indices = None

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.KIND == other.KIND and self.name == other.name and self.types == other.types

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.KIND, self.name, tuple(self.types)))

    def write_to_pool(self, pool):
        self._name_index = pool.multiname_pool.index_for(self.name)
        self._types_indices = [pool.multiname_pool.index_for(t) for t in self.types]

    def serialize(self):
        assert self._name_index is not None, "Please call write_to_pool before serializing"
        assert self._types_indices is not None, "Please call write_to_pool before serializing"
        return ''.join([chr(self.KIND), u32(self._name_index), u32(len(self._types_indices))] + [u32(a) for a in self._types_indices])

    def multiname(self):
        return self

# ======================================
# Constant Pool
# ======================================

class AbcConstantPool(object):

    write_to = "pool"
    
    def __init__(self):
        self.int_pool       = ValuePool(0, self)
        self.uint_pool      = ValuePool(0, self)
        self.double_pool    = ValuePool(float("nan"), self)
        self.utf8_pool      = ValuePool(object(), self) # don't use "" because multinames expect "*"
        self.namespace_pool = ValuePool(ANY_NAMESPACE, self)
        self.nsset_pool     = ValuePool(NO_NAMESPACE_SET, self)
        self.multiname_pool = ValuePool(ANY_NAME, self, debug=True)

    def write(self, value):
        if hasattr(value, "write_to_pool"):
            value.write_to_pool(self)
        
    def has_RTNS(self, m):
        return m.KIND in (TYPE_MULTINAME_RtqName,
                          TYPE_MULTINAME_RtqNameA,
                          TYPE_MULTINAME_RtqNameL,
                          TYPE_MULTINAME_RtqNameLA)

    def has_RTName(self, m):
        return m.KIND in (TYPE_MULTINAME_MultinameL,
                          TYPE_MULTINAME_MultinameLA,
                          TYPE_MULTINAME_RtqNameL,
                          TYPE_MULTINAME_RtqNameLA)

    def serialize(self):

        def double(double):
            return struct.pack("<d", double)

        def utf8(string):
            return u32(len(string)) + string
        
        def serializable(item):
            return item.serialize()
        
        def write_pool(pool, fn):
            return u32(len(pool)) + ''.join(fn(i) for i in pool)
        
        buffer = ""
        buffer += write_pool(self.int_pool, u32)
        buffer += write_pool(self.uint_pool, u32)
        buffer += write_pool(self.double_pool, double)
        buffer += write_pool(self.utf8_pool, utf8)
        buffer += write_pool(self.namespace_pool, serializable)
        buffer += write_pool(self.nsset_pool, serializable)
        buffer += write_pool(self.multiname_pool, serializable)

        return buffer
        
