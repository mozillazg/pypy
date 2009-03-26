class W_Object(object):
    """Base class for all io objects"""
    def __init__(self, space, protos = []):
        self.slots  = {}
        self.protos = list(protos)
        self.space = space
    
    def lookup(self, name):
        try:
            return self.slots[name]
        except KeyError:
            pass
        for x in self.protos:
            t = x.lookup(name)
            if t is not None:
                return t
        
class W_Number(W_Object):
    """Number"""
    def __init__(self, space, value):
        self.value = value
        W_Object.__init__(self, space, [space.w_number])
    
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and 
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self == other    

class W_List(W_Object):
    pass
class W_Sequence(W_Object):
    pass

class W_CFunction(W_Object):
    def __init__(self, space, function):
        self.function = function
        W_Object.__init__(self, space)
        
    def apply(self, w_receiver, w_message):
        return self.function(w_receiver, w_message, None)
    
class W_Message(W_Object):
    def __init__(self, space, name, arguments, next = None):
        self.name = name
        self.literal_value = parse_literal(space, name)
        self.arguments = arguments
        self.next = next
        W_Object.__init__(self, space)

    def __repr__(self):
        return "Message(%r, %r, %r)" % (self.name, self.arguments, self.next)

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and 
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self == other
    def eval(self, w_receiver):
        if self.literal_value is not None:
            w_result = self.literal_value
        else:
            w_method = w_receiver.lookup(self.name)
            w_result = w_method.apply(w_receiver, self)
        if self.next:
            #TODO: optimize
            return self.next.eval(w_result)
        else:
            return w_result
                
def parse_literal(space, literal):
    for t in [int, float, lambda x: int(x, 16)]:
        try:
            return W_Number(space, t(literal))
        except ValueError:
            pass
    
