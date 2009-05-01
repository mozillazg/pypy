class W_Object(object):
    """Base class for all io objects"""
    def __init__(self, space, protos = []):
        self.slots  = {}
        self.protos = list(protos)
        self.space = space
    
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and 
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self == other

    def lookup(self, name):
        try:
            return self.slots[name]
        except KeyError:
            pass
        for x in self.protos:
            t = x.lookup(name)
            if t is not None:
                return t

    def apply(self, space, w_receiver, w_message, w_context):
        return self
        
    def clone(self):
        return W_Object(self.space, [self])
        
class W_Number(W_Object):
    """Number"""
    def __init__(self, space, value, protos = None):
        self.value = value
        if protos is None:
            pp = [space.w_number]
        else:
            pp = protos
        W_Object.__init__(self, space, pp) 
        
    def clone(self):
        cloned = W_Number(self.space, self.value)
        cloned.protos = [self]
        return cloned

class W_List(W_Object):
    def __init__(self, space, protos = [], items = []):
        W_Object.__init__(self, space, protos)
        self.items = items

    def append(self, w_items):
        self.items += w_items
        
    def __getitem__(self, index):
        try:
            return self.items[index]
        except IndexError:
            return self.space.w_nil
        
        
    def clone(self):
        return W_List(self.space, [self], list(self.items))

    def clone_and_init(self, space, items):
        l = self.clone()
        l.items += items
        return l
        
class W_ImmutableSequence(W_Object):
    def __init__(self, space, string):
        self.value = string
    

class W_CFunction(W_Object):
    def __init__(self, space, function):
        self.function = function
        W_Object.__init__(self, space)
        
    def apply(self, space, w_receiver, w_message, w_context):
        return self.function(space, w_receiver, w_message, w_context)
    
class W_Message(W_Object):
    def __init__(self, space, name, arguments, next = None):
        self.name = name
        self.literal_value = parse_literal(space, name)
        self.arguments = arguments
        self.next = next
        W_Object.__init__(self, space)

    def __repr__(self):
        return "Message(%r, %r, %r)" % (self.name, self.arguments, self.next)

    
    def eval(self, space, w_receiver, w_context):
        if self.name == ';':
            # xxx is this correct?
            w_result = w_context
        elif self.literal_value is not None:
            w_result = self.literal_value
        else:
            w_method = w_receiver.lookup(self.name)
            assert w_method is not None, 'Method "%s" not found in "%s"' % (self.name, w_receiver.__class__)
            w_result = w_method.apply(space, w_receiver, self, w_context)
        if self.next:
            #TODO: optimize
            return self.next.eval(space, w_result, w_context)
        else:
            return w_result
  
class W_Block(W_Object):
    def __init__(self, space, arguments, body, activateable=True, protos=[]):
        self.arguments = arguments
        self.body = body
        W_Object.__init__(self, space, protos)
        self.activateable = activateable
        
    def apply(self, space, w_receiver, w_message, w_context):
        # TODO: create and populate call object
        if self.activateable:
            return self.call(space, w_receiver, w_message, w_context)
        return self
        
    def call(self, space, w_receiver, w_message, w_context):
        w_locals = self.space.w_locals.clone()
        assert w_locals is not None
        args = list(self.arguments)
        
        for arg in w_message.arguments:
            try:
                w_locals.slots[args.pop(0)] = arg.eval(space, w_receiver, w_context)
            except IndexError:
                break
                
        for arg_name in args:
            w_locals.slots[arg_name] = space.w_nil
        
        if self.activateable:
            w_locals.protos = [w_receiver]
            w_locals.slots['self'] = w_receiver
        else:
            w_locals.protos = [w_context]
            w_locals.slots['self'] = w_context
            
        return self.body.eval(space, w_locals, w_context)
            
    
    def clone(self):
        return W_Block(self.space, self.arguments, self.body, self.activateable, [self])
        
    def clone_and_init(self, space, arguments, body, activateable):
        return W_Block(space, arguments, body, activateable, [self])
        
def parse_hex(string):
    if not string.startswith("0x"):
        raise ValueError
    return int(string, 16) 
    
def parse_literal(space, literal):
    for t in [int, float, parse_hex]:
        try:
            return W_Number(space, t(literal))
        except ValueError:
            pass
    if literal.startswith('"') and literal.endswith('"'):
        return W_ImmutableSequence(space, literal[1:-1])