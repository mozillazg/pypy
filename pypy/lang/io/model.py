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
    
    def hash(self):
        h = 0
        for w_x in self.slots:
            h += w_x.hash()
        for x in self.protos:
            h += hash(x)
        
        return h
        
    def lookup(self, name, seen=None):
        if seen is None:
            seen = {}
        else:
            if self in seen:
                return None
        seen[self] = None

        try:
            return self.slots[name]
        except KeyError:
            pass
        for x in self.protos:            
            t = x.lookup(name, seen)
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
        
    def hash(self):
        return hash(self.value)

class W_List(W_Object):
    def __init__(self, space, protos = [], items = []):
        W_Object.__init__(self, space, protos)
        self.items = items

    def extend(self, items_w):
        self.items.extend(items_w)
        
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
    
    def hash(self):
        h = 0
        for x in self.items:
            h += x.hash()
        return h
        
class W_Map(W_Object):
    """A key/value dictionary appropriate for holding large key/value collections."""
    def __init__(self, space, protos = [], items = {}):
        W_Object.__init__(self, space, protos)
        self.items = items
        
    def clone(self):
        return W_Map(self.space, [self], dict(self.items))
        
    def hash(self):
        h = 0
        for key, val in self.items:
            h += key + val.hash()
        return h
    
    def at(self, w_key):
        return self.items[w_key.hash()].value
    
    def at_put(self, w_key, w_value):
        self.items[w_key.hash()] = MapEntry(w_key, w_value)
        
    def empty(self):
        self.items.clear()
    
    def has_key(self, w_key):
        return w_key.hash() in self.items
        
    def size(self):
        return len(self.items)
    
    def remove_at(self, w_key):
        try:
            del(self.items[w_key.hash()])
        except Exception, e:
            pass
            
    def has_value(self, w_value):
        for x in self.items.values():
            if x.value == x:
                return True
        return False
        
    def values(self):
        return [x.value for x in self.items.values()]
        
    def foreach(self, space, key_name, value_name, w_body, w_context):
        for item in self.items.values():
            w_context.slots[key_name] = item.key
            w_context.slots[value_name] = item.value
            t = w_body.eval(space, w_context, w_context)
        return t 
        
    def keys(self):
        return [x.key for x in self.items.values()]
        
class MapEntry(object):
    def __init__(self, w_key, w_value):
        self.key = w_key
        self.value = w_value
    
        
class W_ImmutableSequence(W_Object):
    def __init__(self, space, string):
        self.value = string
        
    def hash(self):
        return hash(self.value)

class W_CFunction(W_Object):
    def __init__(self, space, function):
        self.function = function
        W_Object.__init__(self, space)
        
    def apply(self, space, w_receiver, w_message, w_context):
        return self.function(space, w_receiver, w_message, w_context)
    
    def hash(self):
        return hash(self.function)
        
class W_Message(W_Object):
    def __init__(self, space, name, arguments, next = None):
        self.name = name
        self.literal_value = parse_literal(space, name)
        self.arguments = arguments
        self.next = next
        W_Object.__init__(self, space, [space.w_message])

    def __repr__(self):
        return "Message(%r, %r, %r)" % (self.name, self.arguments, self.next)

    def hash(self):
        h = hash(self.name)
        for x in self.arguments:
            h += x.hash()
        return h
        
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
            return self.next.eval(space, w_result, w_receiver)
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
        w_call = self.space.w_call.clone()
        assert w_locals is not None
        assert w_call is not None
        
        args = list(self.arguments)
        n_params = len(w_message.arguments)
        for i in range(len(args)):
            if i < n_params:
                w_locals.slots[args[i]] = w_message.arguments[i].eval(space, w_receiver, w_context)
            else:
                w_locals.slots[args[i]] = space.w_nil
        
        if self.activateable:
            w_locals.protos = [w_receiver]
            w_locals.slots['self'] = w_receiver
        else:
            w_locals.protos = [w_context]
            w_locals.slots['self'] = w_context
        
        w_locals.slots['call'] = w_call
        w_call.slots['message'] = w_message
        return self.body.eval(space, w_locals, w_context)
            
    
    def clone(self):
        return W_Block(self.space, self.arguments, self.body, self.activateable, [self])
        
    def clone_and_init(self, space, arguments, body, activateable):
        return W_Block(space, arguments, body, activateable, [self])
        
    def hash(self):
        h = self.body.hash()
        for x in self.arguments:
            h += x.hash()
        return h
        
        
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