

class SpecNode(object):
    __slots__ = ()

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        resultlist.append(valuebox)


class NotSpecNode(SpecNode):
    __slots__ = ()


prebuiltNotSpecNode = NotSpecNode()


class FixedClassSpecNode(SpecNode):
    def __init__(self, known_class):
        self.known_class = known_class


class VirtualInstanceSpecNode(FixedClassSpecNode):
    def __init__(self, known_class, fields):
        FixedClassSpecNode.__init__(self, known_class)
        self.fields = fields
