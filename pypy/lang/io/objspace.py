from pypy.rlib.objectmodel import instantiate
from pypy.lang.io.model import W_Number, W_Object, W_CFunction, W_Block, W_Message, W_List, W_Map, W_ImmutableSequence
from pypy.lang.io.coroutinemodel import W_Coroutine
from pypy.lang.io.register import cfunction_definitions

import pypy.lang.io.number
import pypy.lang.io.object
import pypy.lang.io.block
import pypy.lang.io.list
import pypy.lang.io.call
import pypy.lang.io.message
import pypy.lang.io.map
import pypy.lang.io.coroutine
import pypy.lang.io.sequence

class ObjSpace(object):
    """docstring for ObjSpace"""
    def __init__(self):
        self.w_object = W_Object(self)

        self.w_lobby = W_Object(self)
        self.w_protos = W_Object(self)
        self.w_core = W_Object(self)
        self.w_locals = W_Object(self)
        self.w_true = W_Object(self, [self.w_object])
        self.w_false = W_Object(self, [self.w_object])
        self.w_nil = W_Object(self, [self.w_object])
        self.w_list = W_List(self, [self.w_object])
        self.w_call = W_Object(self, [self.w_object])
        self.w_map = W_Map(self, [self.w_object])
        self.w_coroutine = W_Coroutine.w_getcurrent(self)
        # flow control objects
        self.w_normal = W_Object(self, [self.w_object])
        self.w_break = W_Object(self, [self.w_object])
        self.w_continue = W_Object(self, [self.w_object])
        self.w_return = W_Object(self, [self.w_object])
        self.w_eol = W_Object(self, [self.w_object])
        
        # XXX TODO: change this when Sequence is implemented
        self.w_sequence = W_ImmutableSequence(self, '',[self.w_object])
        self.w_immutable_sequence = W_ImmutableSequence(self, '', [self.w_sequence])
        # default stop state
        self.stop_status = self.w_normal
        self.w_return_value = self.w_nil
        self.init_w_object()        
        
        self.init_w_protos()
        
        self.init_w_list()

        self.init_w_message()

        self.w_block = W_Block(self, [], W_Message(self, 'nil', []), False, [self.w_object])
        self.init_w_block()
        
        self.init_w_lobby()
        
        self.init_w_number()
        
        
        self.init_w_core()
        
        self.init_w_call()
         
        self.init_w_map()

        self.init_w_coroutine()
        
        self.init_w_flow_objects()
        
        self.init_w_sequence()
        
        self.init_stored_messages()

        
    def init_w_map(self):
        for key, function in cfunction_definitions['Map'].items():
            self.w_map.slots[key] = W_CFunction(self, function)
            
    def init_w_call(self):
        for key, function in cfunction_definitions['Call'].items():
            self.w_call.slots[key] = W_CFunction(self, function)
            
    def init_w_protos(self):
        self.w_protos.protos.append(self.w_core)
        self.w_protos.slots['Core'] = self.w_core
        
    def init_w_block(self):
        for key, function in cfunction_definitions['Block'].items():
            self.w_block.slots[key] = W_CFunction(self, function)
    
    def init_w_list(self):
        for key, function in cfunction_definitions['List'].items():
            self.w_list.slots[key] = W_CFunction(self, function)
            
    def init_w_core(self):
        self.w_core.protos.append(self.w_object)
        self.w_core.slots['Locals'] = self.w_locals
        self.w_core.slots['Block'] = self.w_block
        self.w_core.slots['Coroutine'] = self.w_coroutine
        self.w_core.slots['Object'] = self.w_object
        self.w_core.slots['true'] = self.w_true
        self.w_core.slots['false'] = self.w_false
        self.w_core.slots['nil'] = self.w_nil
        self.w_core.slots['List'] = self.w_list
        self.w_core.slots['Call'] = self.w_call
        self.w_core.slots['Map'] = self.w_map
        self.w_core.slots['Message'] = self.w_message
        self.w_core.slots['Number'] = self.w_number
        self.w_core.slots['Sequence'] = self.w_sequence
        self.w_core.slots['ImmutableSequence'] = self.w_immutable_sequence

    def init_w_number(self):
        self.w_number = instantiate(W_Number)
        W_Object.__init__(self.w_number, self)   
        self.w_number.protos = [self.w_object]     
        self.w_number.value = 0
        for key, function in cfunction_definitions['Number'].items():
            self.w_number.slots[key] = W_CFunction(self, function)
            
    def init_w_message(self):
        self.w_message = instantiate(W_Message)
        W_Object.__init__(self.w_message, self)   
        self.w_message.protos = [self.w_object]     
        self.w_message.name = "Unnamed"
        for key, function in cfunction_definitions['Message'].items():
            self.w_message.slots[key] = W_CFunction(self, function)

    def init_w_lobby(self):
        self.w_lobby.protos.append(self.w_protos)
        self.w_object.protos.append(self.w_lobby)
        self.w_lobby.slots['Lobby'] = self.w_lobby
        self.w_lobby.slots['Protos'] = self.w_protos

    def init_w_object(self):
        for key, function in cfunction_definitions['Object'].items():
            self.w_object.slots[key] = W_CFunction(self, function)
            
    def init_w_flow_objects(self):
        # Flow control: Normal
        self.w_core.slots['Normal'] = self.w_normal
        self.w_core.slots['Normal'].slots['type'] = W_ImmutableSequence(self, 'Normal')
    	
    	# Flow control: Break
    	self.w_core.slots['Break'] = self.w_break
        self.w_core.slots['Break'].slots['type'] = W_ImmutableSequence(self, 'Break')

    	# Flow control: Continue
        self.w_core.slots['Continue'] = self.w_continue
        self.w_core.slots['Continue'].slots['type'] = W_ImmutableSequence(self, 'Continue')

    	# Flow control: Return
    	self.w_core.slots['Return'] = self.w_return
        self.w_core.slots['Return'].slots['type'] = W_ImmutableSequence(self, 'Return')

    	# Flow control: Eol
    	self.w_core.slots['Eol'] = self.w_eol
        self.w_core.slots['Eol'].slots['type'] = W_ImmutableSequence(self, 'Eol')
        
        
    def init_w_coroutine(self):
        for key, function in cfunction_definitions['Coroutine'].items():
            self.w_coroutine.slots[key] = W_CFunction(self, function)
        
    def init_w_sequence(self):
        for key, function in cfunction_definitions['Sequence'].items():
            self.w_sequence.slots[key] = W_CFunction(self, function)
            
    def break_status(self, result):
        self.stop_status = self.w_break
        self.w_return_value = result
        
    def normal_status(self):
        self.stop_status = self.w_normal
        self.w_return_value = self.w_nil
        
    def is_normal_status(self):
        return self.stop_status == self.w_normal
        
    def continue_status(self):
        self.stop_status = self.w_continue

    def is_continue_status(self):
        return self.stop_status == self.w_continue    

    def return_status(self, result):
        self.stop_status = self.w_return
        self.w_return_value = result
        
    def newbool(self, value):
        if value:
            return self.w_true
        return self.w_false
        
    def init_stored_messages(self):
        self.w_print_message = W_Message(self, 'print', [])