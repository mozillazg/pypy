
from pypy.jit.metainterp.history import ConstInt

class SpecNode(object):

    def expand_boxlist(self, instnode, newboxlist):
        newboxlist.append(instnode.source)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        resultlist.append(valuebox)

    def adapt_to(self, instnode):
        instnode.escaped = True

class NotSpecNode(SpecNode):
    def mutate_nodes(self, instnode):
        pass

    def equals(self, other):
        if type(other) is NotSpecNode:
            return True
        return False

    def matches(self, other):
        # NotSpecNode matches everything
        return True

class FixedClassSpecNode(SpecNode):
    def __init__(self, known_class):
        self.known_class = known_class

    def mutate_nodes(self, instnode):
        from pypy.jit.metainterp.optimize import InstanceNode
        
        if instnode.cls is None:
            instnode.cls = InstanceNode(self.known_class)
        else:
            assert instnode.cls.source.equals(self.known_class)

    def equals(self, other):
        if type(other) is not FixedClassSpecNode:
            return False
        else:
            assert isinstance(other, FixedClassSpecNode) # make annotator happy
            return self.known_class.equals(other.known_class)

    def matches(self, instnode):
        if instnode.cls is None:
            return False
        return instnode.cls.source.equals(self.known_class)

class SpecNodeWithFields(FixedClassSpecNode):
    def __init__(self, known_class, fields):
        FixedClassSpecNode.__init__(self, known_class)
        self.fields = fields

    def mutate_nodes(self, instnode):
        FixedClassSpecNode.mutate_nodes(self, instnode)
        curfields = {}
        for ofs, subspecnode in self.fields:
            subinstnode = instnode.origfields[ofs]
            # should really be there
            subspecnode.mutate_nodes(subinstnode)
            curfields[ofs] = subinstnode
        instnode.curfields = curfields

    def equals(self, other):
        if not self.known_class.equals(other.known_class):
            return False
        elif len(self.fields) != len(other.fields):
            return False
        else:
            for i in range(len(self.fields)):
                key, value = self.fields[i]
                otherkey, othervalue = other.fields[i]
                if key != otherkey:
                    return False
                if not value.equals(othervalue):
                    return False
            return True

    def matches(self, instnode):
        # XXX think about details of virtual vs virtualizable
        if not FixedClassSpecNode.matches(self, instnode):
            return False
        for key, value in self.fields:
            if key not in instnode.curfields:
                return False
            if value is not None and not value.matches(instnode.curfields[key]):
                return False
        return True

    def expand_boxlist(self, instnode, newboxlist):
        for ofs, subspecnode in self.fields:
            subinstnode = instnode.curfields[ofs]  # should really be there
            subspecnode.expand_boxlist(subinstnode, newboxlist)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        for ofs, subspecnode in self.fields:
            cls = self.known_class.getint()
            tp = cpu.typefor(ofs)
            fieldbox = cpu.execute_operation('getfield_gc',
                                             [valuebox, ConstInt(ofs)],
                                             tp)
            subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)

    def adapt_to(self, instnode):
        for ofs, subspecnode in self.fields:
            subspecnode.adapt_to(instnode.curfields[ofs])

class VirtualizableSpecNode(SpecNodeWithFields):

    def equals(self, other):
        if not isinstance(other, VirtualizableSpecNode):
            return False
        return SpecNodeWithFields.equals(self, other)

    def expand_boxlist(self, instnode, newboxlist):
        newboxlist.append(instnode.source)        
        SpecNodeWithFields.expand_boxlist(self, instnode, newboxlist)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        resultlist.append(valuebox)
        SpecNodeWithFields.extract_runtime_data(self, cpu, valuebox, resultlist)

    def adapt_to(self, instnode):
        instnode.escaped = True
        SpecNodeWithFields.adapt_to(self, instnode)

class VirtualInstanceSpecNode(SpecNodeWithFields):

    def mutate_nodes(self, instnode):
        SpecNodeWithFields.mutate_nodes(self, instnode)
        instnode.virtual = True

    def equals(self, other):
        if not isinstance(other, VirtualInstanceSpecNode):
            return False
        return SpecNodeWithFields.equals(self, other)

