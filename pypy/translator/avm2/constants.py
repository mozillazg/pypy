
import struct
from pypy.translator.avm2.util import serialize_u32 as u32

# ======================================
# Constants
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
TYPE_MULTINAME_QName              = 0x07
TYPE_MULTINAME_QNameA             = 0x0D
TYPE_MULTINAME_Multiname          = 0x09
TYPE_MULTINAME_MultinameA         = 0x0E
TYPE_MULTINAME_RtqName            = 0x0F
TYPE_MULTINAME_RtqNameA           = 0x10
TYPE_MULTINAME_RtqNameL           = 0x11
TYPE_MULTINAME_RtqNameLA          = 0x12
TYPE_MULTINAME_NameL              = 0x13
TYPE_MULTINAME_NameLA             = 0x14
TYPE_MULTINAME_MultinameL         = 0x1B
TYPE_MULTINAME_MultinameLA        = 0x1C

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
        return self.name == other.name and self.kind == other.kind

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
        return len(self) == len(other) and all(n1 == n2 for n1, n2 in zip(self.namespaces, other.namespaces))

    def __ne__(self, other):
        return not self == other

    def write_to_pool(self, pool):
        self._namespace_indices = [pool.namespace_pool.index_for(ns) for ns in self.namespaces]
    
    def serialize(self):
        assert self._namespace_indices is not None, "Please call write_to_pool before serializing"
        return u32(len(self.namespaces)) + ''.join(u32(index) for index in self._namespace_indices)
        

NO_NAMESPACE  = Namespace(TYPE_NAMESPACE_Namespace, "")
ANY_NAMESPACE = Namespace(TYPE_NAMESPACE_Namespace, "*")

NO_NAMESPACE_SET = NamespaceSet()

# ======================================
# Multinames
# ======================================

class MultinameL(object):
    KIND = TYPE_MULTINAME_MultinameL
    
    def __init__(self, ns_set):
        self.ns_set = ns_set
        self._ns_set_index = None

    def __eq__(self, other):
        return self.kind == other.kind and self.ns_set == other.ns_set

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.kind, self.ns_set))
    
    def write_to_pool(self, pool):
        self._ns_set_index = pool.nsset_pool.index_for(self.ns_set)

    def serialize(self):
        assert self._ns_set_index is not None, "Please call write_to_pool before serializing"
        return chr(self.KIND) + u32(self._ns_set_index)

class MultinameLA(MultinameL):
    KIND = TYPE_MULTINAME_MultinameLA

class Multiname(MultinameL):
    KIND = TYPE_MULTINAME_Multiname
    
    def __init__(self, name, ns_set):
        super(Multiname, self).__init__(ns_set)
        self.name = name
        self._name_index = None

    def __eq__(self, other):
        return self.kind == other.kind and self.name == other.name

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.kind, self.name))

    def write_to_pool(self, pool):
        super(Multiname, self).write_to_pool(pool)
        self._name_index = pool.utf8_pool.index_for(self.name)

    def serialize(self):
        assert self._name_index is not None, "Please call write_to_pool before serializing"
        assert self._ns_set_index is not None, "Please call write_to_pool before serializing"
        return chr(self.kind) + u32(self._name_index) + u32(self._ns_set_index)

class MultinameA(Multiname):
    KIND = TYPE_MULTINAME_MultinameA


class QName(object):
    KIND = TYPE_MULTINAME_QName
    
    def __init__(self, name, ns):
        self.name = name
        self.ns = ns

        self._name_index = None
        self._ns_index = None

    def __eq__(self, other):
        return self.kind == other.kind and self.name == other.name and self.ns == other.ns

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.kind, self.name, self.ns))
    
    def write_to_pool(self, pool):
        self._name_index = pool.utf8_pool.index_for(self.name)
        self._ns_index = pool.namespace_pool.index_for(self.ns)
        
    def serialize(self):
        assert self._name_index is not None, "Please call write_to_pool before serializing"
        assert self._ns_index is not None, "Please call write_to_pool before serializing"
        return chr(self.kind) + u32(self._ns_index) + u32(self._name_index)

class QNameA(QName):
    KIND = TYPE_MULTINAME_QNameA
    
class RtqNameL(object):
    KIND = TYPE_MULTINAME_RtqNameL
    
    def serialize(self):
        return chr(self.kind)

    def __eq__(self, other):
        return self.kind == other.kind

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.kind))

class RtqNameLA(RtqNameL):
    KIND = TYPE_MULTINAME_RtqNameLA

class RtqName(object):
    KIND = TYPE_MULTINAME_RtqName

    def __init__(self, name):
        self.name = name
        self._name_index = None

    def write_to_pool(self, pool):
        self._name_index = pool.utf8_pool.index_for(name)

    def serialize(self):
        assert self._name_index is not None, "Please call write_to_pool before serializing"
    
# ======================================
# Constant Pool
# ======================================

class ValuePool(object):
    
    def __init__(self, default):
        self.index_map = {}
        self.pool      = []
        self.default = default

    def index_for(self, value):
        if value == self.default:
            return 0
        
        if value in self.index_map:
            return self.index_map[value]
        
        self.pool.append(value)
        index = len(self.pool)
        self.index_map[value] = index
        return index
    
    def value_at(self, index):
        if index == 0:
            return self.default
        
        if index < len(self.pool):
            return self.pool[index]
        
        return None

class AbcConstantPool(object):
    
    def __init__(self):
        self.int_pool       = ValuePool(0)
        self.uint_pool      = ValuePool(0)
        self.double_pool    = ValuePool(float("nan"))
        self.utf8_pool      = ValuePool("")
        self.namespace_pool = ValuePool(ANY_NAMESPACE)
        self.nsset_pool     = ValuePool(NO_NAMESPACE_SET)
        self.multiname_pool = ValuePool()
        
    def has_RTNS(self, index):
        return self.multiname_pool[index].kind in (TYPE_MULTINAME_RtqName,
                                                   TYPE_MULTINAME_RtqNameA,
                                                   TYPE_MULTINAME_RtqNameL,
                                                   TYPE_MULTINAME_RtqNameLA)

    def has_RTName(self, index):
        return self.multiname_pool[index].kind in (TYPE_MULTINAME_MultinameL,
                                                   TYPE_MULTINAME_MultinameLA,
                                                   TYPE_MULTINAME_RtqNameL,
                                                   TYPE_MULTINAME_RtqNameLA)

    def serialize(self):

        def double(double):
            return struct.pack("<d", double)

        def utf8(string):
            return u32(len(string)) + string
        
        def serializable(item):
            item.write_to_pool(self)
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
        
