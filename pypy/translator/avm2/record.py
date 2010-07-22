
from pypy.rpython.ootypesystem import ootype
from pypy.translator.avm2.node import ClassNodeBase

from mech.fusion.avm2.constants import QName
from mech.fusion.avm2.interfaces import IMultiname

class Record(ClassNodeBase):
    def __init__(self, db, record, name):
        self.db = db
        self.cts = db.genoo.TypeSystem(db)
        self.record = record
        self.name = name

    def __hash__(self):
        return hash(self.record)

    def __eq__(self, other):
        return type(self) == type(other) and self.record == other.record

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return '<Record %s>' % self.name

    def get_type(self):
        return QName(self.name)

    def get_name(self):
        return self.name

    def get_base_class(self):
        return QName("Object")

    def get_fields(self):
        return self.record._fields.iteritems()

    def _fieldToString(self, ilasm, fieldnum):
        f_name = 'item%d' % (fieldnum,)
        FIELD_TYPE, f_default = self.record._fields[f_name]
        if FIELD_TYPE is ootype.Void:
            return True
        ilasm.push_this()
        ilasm.emit('getproperty', IMultiname(f_name))
        ilasm.emit('convert_s')

    def render_toString(self, ilasm):
        for f_name in self.record._fields:
            if not f_name.startswith('item'):
                return # it's not a tuple

        ilasm.begin_method('toString', [], QName("String"))
        ilasm.load("(")
        fieldlen = len(self.record._fields)-1
        for i in xrange(fieldlen):
            if self._fieldToString(ilasm, i):
                continue
            ilasm.emit('add')
            ilasm.load(", ")
            ilasm.emit('add')
        self._fieldToString(ilasm, fieldlen)
        ilasm.emit('add')
        ilasm.load(")")
        ilasm.emit('add')
        ilasm.emit('returnvalue')
        ilasm.exit_context()

    # def _equals(self):
    #     # field by field comparison
    #     record_type = self.cts.lltype_to_cts(self.record)
    #     self.ilasm.begin_function('Equals', [('object', 'obj')], 'bool',
    #                               False, 'virtual', 'instance', 'default')
    #     self.ilasm.locals([(record_type, 'self')])
    #     self.ilasm.opcode('ldarg.1')
    #     self.ilasm.opcode('castclass', record_type.classname())
    #     self.ilasm.opcode('stloc.0')

    #     equal = 'bool [pypylib]pypy.runtime.Utils::Equal<%s>(!!0, !!0)'
    #     self.ilasm.opcode('ldc.i4', '1')
    #     for f_name, (FIELD_TYPE, default) in self.record._fields.iteritems():
    #         if FIELD_TYPE is ootype.Void:
    #             continue
    #         f_type = self.cts.lltype_to_cts(FIELD_TYPE)
    #         f_name = self.cts.escape_name(f_name)
    #         self.ilasm.opcode('ldarg.0')
    #         self.ilasm.get_field((f_type, record_type.classname(), f_name))
    #         self.ilasm.opcode('ldloc.0')
    #         self.ilasm.get_field((f_type, record_type.classname(), f_name))
    #         self.ilasm.call(equal % f_type)
    #         self.ilasm.opcode('and')

    #     self.ilasm.opcode('ret')
    #     self.ilasm.end_function()

    # def _getHashCode(self):
    #     record_type = self.cts.lltype_to_cts(self.record)
    #     self.ilasm.begin_function('GetHashCode', [], 'int32', False, 'virtual', 'instance', 'default')
    #     gethash = 'int32 [pypylib]pypy.runtime.Utils::GetHashCode<%s>(!!0)'

    #     self.ilasm.opcode('ldc.i4.0') # initial hash
    #     if self.record._fields:
    #         for f_name, (FIELD_TYPE, default) in self.record._fields.iteritems():
    #             if FIELD_TYPE is ootype.Void:
    #                 continue
    #             else:
    #                 # compute the hash for this field
    #                 f_name = self.cts.escape_name(f_name)
    #                 f_type = self.cts.lltype_to_cts(FIELD_TYPE)
    #                 self.ilasm.opcode('ldarg.0')
    #                 self.ilasm.get_field((f_type, record_type.classname(), f_name))
    #                 self.ilasm.call(gethash % f_type)

    #                 # xor with the previous value
    #                 self.ilasm.opcode('xor')
                    
    #     self.ilasm.opcode('ret')
    #     self.ilasm.end_function()
