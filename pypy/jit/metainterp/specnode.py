

class SpecNode(object):
    __slots__ = ()

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        resultlist.append(valuebox)


class NotSpecNode(SpecNode):
    __slots__ = ()

    def _equals(self, other):   # for tests only
        return type(other) is NotSpecNode


prebuiltNotSpecNode = NotSpecNode()


class FixedClassSpecNode(SpecNode):
    def __init__(self, known_class):
        self.known_class = known_class

    def _equals(self, other):   # for tests only
        return (type(other) is FixedClassSpecNode and
                self.known_class.equals(other.known_class))


class VirtualInstanceSpecNode(FixedClassSpecNode):
    def __init__(self, known_class, fields):
        FixedClassSpecNode.__init__(self, known_class)
        self.fields = fields

    def _equals(self, other):   # for tests only
        ok = (type(other) is VirtualInstanceSpecNode and
              self.known_class.equals(other.known_class) and
              len(self.fields) == len(other.fields))
        if ok:
            for (o1, s1), (o2, s2) in zip(self.fields, other.fields):
                ok = ok and o1 == o2 and s1._equals(s2)
        return ok
