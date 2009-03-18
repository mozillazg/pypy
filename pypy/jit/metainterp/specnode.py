from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp import executor
from pypy.rlib.objectmodel import r_dict

def av_eq(self, other):
    return self.sort_key() == other.sort_key()

def av_hash(self):
    return self.sort_key()

class BoxRetriever(object):
    def __init__(self):
        self.lists = [[]]
        self.current = self.lists[0]

    def flatten(self):
        res = self.lists[0]
        for i in range(1, len(self.lists)):
            res.extend(self.lists[i])
        return res

    def extend(self, group):
        while len(self.lists) <= group:
            self.lists.append([])
        self.current = self.lists[group]

    def append(self, box):
        self.current.append(box)

    def reset(self):
        self.current = self.lists[0]

class SpecNode(object):

    def expand_boxlist(self, instnode, newboxes, start):
        newboxes.append(instnode.source)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        resultlist.append(valuebox)

    def adapt_to(self, instnode, newboxlist, newspecnodes, num):
        instnode.escaped = True

    def mutate_nodes(self, instnode):
        raise NotImplementedError

    def equals(self, other):
        raise NotImplementedError

    def matches(self, other):
        raise NotImplementedError

class RedirectingSpecNode(SpecNode):
    def __init__(self, specnode, group):
        self.redirect_to = specnode
        self.group = group

    def expand_boxlist(self, instnode, newboxes, start):
        newboxes.extend(self.group)
        self.redirect_to.expand_boxlist(instnode, newboxes, start)
        newboxes.reset()

    def extract_runtime_data(self, cpu, valuebox, result):
        result.extend(self.group)
        self.redirect_to.extract_runtime_data(cpu, valuebox, result)
        result.reset()

    def adapt_to(self, *args):
        self.redirect_to.adapt_to(*args)

    def equals(self, other):
        return self.redirect_to.equals(other)

    def matches(self, other):
        return self.redirect_to.matches(other)

class MatchEverythingSpecNode(SpecNode):
    pass

class NotSpecNode(SpecNode):
    def mutate_nodes(self, instnode):
        instnode.cursize = -1

    def equals(self, other):
        if type(other) is NotSpecNode:
            return True
        return False

    def matches(self, other):
        # NotSpecNode matches everything
        return True

class SpecNodeWithBox(NotSpecNode):
    # XXX what is this class used for?
    def __init__(self, box):
        self.box = box
    
    def equals(self, other):
        if type(other) is SpecNodeWithBox:
            return True
        return False

class FixedClassSpecNode(SpecNode):
    def __init__(self, known_class):
        self.known_class = known_class

    def mutate_nodes(self, instnode):
        from pypy.jit.metainterp.optimize import InstanceNode
        
        if instnode.cls is None:
            instnode.cls = InstanceNode(self.known_class, const=True)
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
        curfields = r_dict(av_eq, av_hash)
        for ofs, subspecnode in self.fields:
            if not isinstance(subspecnode, MatchEverythingSpecNode):
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
        if not FixedClassSpecNode.matches(self, instnode):
            return False
        for key, value in self.fields:
            if not isinstance(value, MatchEverythingSpecNode):
                if key not in instnode.curfields:
                    return False
                if value is not None and not value.matches(instnode.curfields[key]):
                    return False
        return True

    def expand_boxlist(self, instnode, newboxlist, start):
        for ofs, subspecnode in self.fields:
            if not isinstance(subspecnode, MatchEverythingSpecNode):
                subinstnode = instnode.curfields[ofs]  # should really be there
                subspecnode.expand_boxlist(subinstnode, newboxlist, start)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        for ofs, subspecnode in self.fields:
            from pypy.jit.metainterp.history import AbstractDescr
            assert isinstance(ofs, AbstractDescr)
            if not isinstance(subspecnode, MatchEverythingSpecNode):
                fieldbox = executor.execute(cpu, rop.GETFIELD_GC,
                                            [valuebox], ofs)
                subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)

    def adapt_to(self, instnode, newboxlist, newspecnodes, num):
        for ofs, subspecnode in self.fields:
            subspecnode.adapt_to(instnode.curfields[ofs], newboxlist,
                                 newspecnodes, num)

class VirtualizedOrDelayedSpecNode(SpecNodeWithFields):
    
    def expand_boxlist(self, instnode, newboxlist, start):
        newboxlist.append(instnode.source)
        SpecNodeWithFields.expand_boxlist(self, instnode, newboxlist, start)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        resultlist.append(valuebox)
        SpecNodeWithFields.extract_runtime_data(self, cpu, valuebox, resultlist)

    def adapt_to(self, instnode, newboxlist, newspecnodes, num):
        instnode.escaped = True
        SpecNodeWithFields.adapt_to(self, instnode, newboxlist, newspecnodes,
                                    num)

class DelayedSpecNode(VirtualizedOrDelayedSpecNode):

    def expand_boxlist(self, instnode, newboxlist, oplist):
        from pypy.jit.metainterp.history import AbstractDescr
        newboxlist.append(instnode.source)
        for ofs, subspecnode in self.fields:
            assert isinstance(subspecnode, SpecNodeWithBox)
            if oplist is None:
                instnode.cleanfields[ofs] = instnode.origfields[ofs]
                newboxlist.append(instnode.curfields[ofs].source)
            else:
                if ofs in instnode.cleanfields:
                    newboxlist.append(instnode.cleanfields[ofs].source)
                else:
                    box = subspecnode.box.clonebox()
                    assert isinstance(ofs, AbstractDescr)
                    oplist.append(ResOperation(rop.GETFIELD_GC,
                       [instnode.source], box, ofs))
                    newboxlist.append(box)

class DelayedFixedListSpecNode(DelayedSpecNode):

   def expand_boxlist(self, instnode, newboxlist, oplist):
       from pypy.jit.metainterp.history import ResOperation
       from pypy.jit.metainterp.resoperation import rop
       from pypy.jit.metainterp.optimize import FixedList
        
       newboxlist.append(instnode.source)
       cls = self.known_class
       assert isinstance(cls, FixedList)
       arraydescr = cls.arraydescr
       for ofs, subspecnode in self.fields:
           assert isinstance(subspecnode, SpecNodeWithBox)
           if oplist is None:
               instnode.cleanfields[ofs] = instnode.origfields[ofs]
               newboxlist.append(instnode.curfields[ofs].source)
           else:
               if ofs in instnode.cleanfields:
                   newboxlist.append(instnode.cleanfields[ofs].source)
               else:
                   box = subspecnode.box.clonebox()
                   oplist.append(ResOperation(rop.GETARRAYITEM_GC,
                      [instnode.source, ofs], box, arraydescr))
                   newboxlist.append(box)

   def extract_runtime_data(self, cpu, valuebox, resultlist):
       from pypy.jit.metainterp.resoperation import rop
       from pypy.jit.metainterp.optimize import FixedList
       from pypy.jit.metainterp.history import check_descr
       
       resultlist.append(valuebox)
       cls = self.known_class
       assert isinstance(cls, FixedList)
       arraydescr = cls.arraydescr
       check_descr(arraydescr)
       for ofs, subspecnode in self.fields:
           fieldbox = executor.execute(cpu, rop.GETARRAYITEM_GC,
                                       [valuebox, ofs], arraydescr)
           subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)

class VirtualizedSpecNode(VirtualizedOrDelayedSpecNode):

    def equals(self, other):
        if not self.known_class.equals(other.known_class):
            return False
        assert len(self.fields) == len(other.fields)
        for i in range(len(self.fields)):
            if (isinstance(self.fields[i][1], MatchEverythingSpecNode) or
                isinstance(other.fields[i][1], MatchEverythingSpecNode)):
                continue
            assert self.fields[i][0].equals(other.fields[i][0])
            if not self.fields[i][1].equals(other.fields[i][1]):
                return False
        return True

    def adapt_to(self, instnode, newboxlist, newspecnodes, num):
        instnode.virtualized = True
        fields = []
        for ofs, subspecnode in self.fields:
            if isinstance(subspecnode, MatchEverythingSpecNode):
                if ofs in instnode.curfields:
                    orignode = instnode.origfields[ofs]
                    node = instnode.curfields[ofs]
                    subspecnode = orignode.intersect(node, {})
                    subspecnode.mutate_nodes(orignode)
                    subspecnode = RedirectingSpecNode(subspecnode, num)
                    subspecnode.expand_boxlist(orignode, newboxlist, None)
                    newspecnodes.append(subspecnode)
                # otherwise we simply ignore unused field
            else:
                subspecnode.adapt_to(instnode.curfields[ofs], newboxlist,
                                     newspecnodes, num)
            fields.append((ofs, subspecnode))
        self.fields = fields

class VirtualizableSpecNode(VirtualizedSpecNode):

    def equals(self, other):
        if not isinstance(other, VirtualizableSpecNode):
            return False
        return VirtualizedSpecNode.equals(self, other)        

class VirtualizableListSpecNode(VirtualizedSpecNode):

    def equals(self, other):
        if not isinstance(other, VirtualizableListSpecNode):
            return False
        return VirtualizedSpecNode.equals(self, other)
    
    def extract_runtime_data(self, cpu, valuebox, resultlist):
        from pypy.jit.metainterp.resoperation import rop
        from pypy.jit.metainterp.optimize import FixedList
        from pypy.jit.metainterp.history import check_descr

        resultlist.append(valuebox)
        cls = self.known_class
        assert isinstance(cls, FixedList)
        arraydescr = cls.arraydescr
        check_descr(arraydescr)
        for ofs, subspecnode in self.fields:
            if not isinstance(subspecnode, MatchEverythingSpecNode):
                fieldbox = executor.execute(cpu, rop.GETARRAYITEM_GC,
                                            [valuebox, ofs], arraydescr)
                subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)

class VirtualSpecNode(SpecNodeWithFields):

    def adapt_to(self, instnode, newboxlist, newspecnodes, num):
        instnode.virtual = True
        return SpecNodeWithFields.adapt_to(self, instnode, newboxlist,
                                           newspecnodes, num)

    def mutate_nodes(self, instnode):
        SpecNodeWithFields.mutate_nodes(self, instnode)
        instnode.virtual = True

class VirtualInstanceSpecNode(VirtualSpecNode):

    def equals(self, other):
        if not isinstance(other, VirtualInstanceSpecNode):
            return False
        return SpecNodeWithFields.equals(self, other)

class VirtualFixedListSpecNode(VirtualSpecNode):

   def __init__(self, known_class, fields, known_length):
       VirtualSpecNode.__init__(self, known_class, fields)
       self.known_length = known_length

   def mutate_nodes(self, instnode):
       VirtualSpecNode.mutate_nodes(self, instnode)
       instnode.cursize = self.known_length

   def equals(self, other):
       if not isinstance(other, VirtualFixedListSpecNode):
           return False
       return SpecNodeWithFields.equals(self, other)
    
   def extract_runtime_data(self, cpu, valuebox, resultlist):
       from pypy.jit.metainterp.resoperation import rop
       from pypy.jit.metainterp.optimize import FixedList
       from pypy.jit.metainterp.history import check_descr
       cls = self.known_class
       assert isinstance(cls, FixedList)
       arraydescr = cls.arraydescr
       check_descr(arraydescr)
       for ofs, subspecnode in self.fields:
           fieldbox = executor.execute(cpu, rop.GETARRAYITEM_GC,
                                       [valuebox, ofs], arraydescr)
           subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)
