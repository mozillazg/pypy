
""" backend generator routines
"""

from pypy.translator.avm import avm1


class AsmGen(object):
    """ AVM1 'assembler' generator routines """
    def __init__(self, name, block=None):
        self.name = name
        self.block = block or Block(True)
        self.scope = (self.block, None, None) # (Code object, Parent scope, Exit callback)

    def new_label(self):
        return self.scope[0].new_label()

    def store_register(self, *args, **kwargs):
        return self.scope[0].store_register(*args, **kwargs)

    def find_register(self, value):
        return self.scope[0].find_register(value)
    
    def action(self, action):
        return self.scope[0].add_action(action)
    
    def enter_scope(self, new_code_obj, exit_callback):
        self.scope = (new_code_obj, self.scope, exit_callback)

    def in_function(self):
        return self.block.FUNCTION_TYPE
    
    def exit_scope(self):
        block_len = self.finalize_block(self, self.scope[0])
        exit_callback = self.scope[2]

        # Go up to the parent scope.
        self.scope = self.scope[1]
        
        self.scope[0].current_offset += len(block_len)
        if exit_callback is not None:
            exit_callback(self)

    def finalize_block(self, block):
        for label, branch_block in block.branch_blocks.iteritems():
            if not branch_block.is_sealed():
                raise Exception, "Branch block hasn't been finalized"
            # Set the label.
            block.labels[label] = block.current_offset
            # Add the actions, which updates current_offset
            for act in branch_block.actions:
                block.add_action(act)
        return block.seal()
        
    
    def begin_function(self, name, arglist):
        self.enter_scope(self.action(avm1.ActionDefineFunction2(name, arglist)))
    
    def begin_prototype_method(self, function_name, _class, arglist):
        self.action(avm1.ActionPush(function_name, "prototype", _class))
        self.action(avm1.ActionGetVariable())
        self.action(avm1.ActionGetMember())
        self.enter_scope(self.action(avm1.ActionDefineFunction2("", arglist, 0)), lambda s: self.action(avm1.ActionSetMember()))
    
    def set_variable(self):
        self.action(avm1.ActionSetVariable())

    def set_member(self):
        self.action(avm1.ActionSetMember())

    def get_member(self):
        self.action(avm1.ActionGetMember())

    def push_arg(self, v):
        if self.in_function() == 0:
            raise Exception, "avm1::push_arg called while not in function scope."
        elif self.in_function() == 1:
            self.push_local(v.name)
        else:
            self.action(avm1.ActionPush(RegisterByValue(v.name)))
    
#    def push_value(self, v):
#        self.action(avm1.ActionPush(v.name))

    def push_this(self, v):
        k = self.find_register("this")
        if k > 0:
            self.action(avm1.ActionPush(RegisterByIndex(k)))
        else:
            self.action(avm1.ActionPush("this"))
            self.action(avm1.ActionGetVariable())
    
    def push_local(self, v):
        k = self.find_register(v.name)
        if k > 0:
            self.action(avm1.ActionPush(RegisterByIndex(k)))
        else:
            self.action(avm1.ActionPush(v.name))
            self.action(avm1.ActionGetVariable())
        
    def push_const(self, v):
        self.action(avm1.ActionPush(v))

    def push_undefined(self):
        self.action(avm1.ActionPush(avm1.Undefined))

    def push_null(self):
        self.action(avm1.ActionPush(avm1.Null))

    def return_stmt(self):
        self.action(avm1.ActionReturn())

    def is_equal(self, value=None):
        if value is not None:
            self.action(avm1.ActionPush(value))
        self.action(avm1.ActionEquals())

    def is_not_equal(self, value=None):
        self.is_equal(value)
        self.action(avm1.ActionNot())
    
    def init_object(self, dict=None):
        if dict is not None:
            self.action(avm1.ActionPush([(b,a) for (a,b) in dict.iteritems()], len(dict)))
        self.action(avm1.ActionInitObject())

    def init_array(self, list=None):
        if list is not None:
            self.action(avm1.ActionPush(list, len(list)))
        self.action(avm1.ActionInitArray())
    
    def call_function(self, func_name): # Assumes the args and number of args are on the stack.
        self.action(avm1.ActionPush(func_name))
        self.action(avm1.ActionCallFunction())
    
    def call_function_constargs(self, func_name, *args):
        self.action(avm1.ActionPush(args, len(args), func_name))
        self.action(avm1.ActionCallFunction())

    def call_method(self, func_name): # Assumes the args and number of args and ScriptObject are on the stack, in that order.
        self.action(avm1.ActionPush(func_name))
        self.action(avm1.ActionCallMethod())
        
    def call_method_constvar(self, _class, func_name): # Assumes vars and number of args are on the stack.
        self.action(avm1.ActionPush(_class))
        self.action(avm1.ActionGetVariable())
        self.action(avm1.ActionPush(func_name))
        self.action(avm1.ActionCallMethod())
    
    def branch_if_true(self, label=""): # Boolean value should be on stack when this is called
        if len(label) < 0:
            label = self.new_label()
        self.scope[0].branch_blocks[label] = Block(False)
        self.action(avm1.ActionIf(label))
        return (label, self.scope[0].branch_blocks[label])

    def set_proto_field(self, _class, member_name): # Assumes the value is on the stack.
        self.action(avm1.ActionPush(member_name, "prototype", _class))
        self.action(avm1.ActionGetVariable())
        self.action(avm1.ActionGetMember())
        self.action(avm1.ActionSwap())
        self.action(avm1.ActionSetMember())
    
    def set_static_field(self, _class, member_name): # Assumes the value is on the stack.
        self.action(avm1.ActionPush(member_name, _class))
        self.action(avm1.ActionGetVariable())
        self.action(avm1.ActionSwap())
        self.action(avm1.ActionSetMember())

    def newobject_constthis(self, obj, *args): # If no args are passed then it is assumed that the args and number of args are on the stack.
        if len(args) > 0:
            self.action(avm1.ActionPush(args, len(args), obj))
        else:
            self.action(avm1.ActionPush(obj))
        self.action(avm1.ActionNewObject())
    
    def newobject(self):
        self.action(avm1.ActionNewObject())
    
#     def store_void(self):
#         if not len(self.right_hand):
#             return
#         v = self.right_hand.pop()
#         if v is not None and v.find('('):
#             self.codegenerator.writeline(v+";")

    # FIXME: will refactor later
    #load_str = load_const
    
    def begin_switch_varname(self, varname):
        self.action(avm1.ActionPush(varname))
        self.action(avm1.ActionGetVariable())
        self.switch_register = self.store_register(varname)
        self.action(avm1.ActionStoreRegister(self.switch_register))
    
    def write_case(self, testee):
        self.action(avm1.ActionPush(avm1.RegisterByIndex(self.switch_register), testee))
        self.action(avm1.ActionStrictEquals())
        if len(self.case_label) < 1:
            self.case_label, self.case_block = self.branch_if_true()
        else:
            self.branch_if_true(self.case_label)

    def write_break(self):
        self.exit_scope()
        self.case_flag = False
        self.case_block = None
    
    def enter_case_branch(self):
        self.enter_scope(self.case_block)
    
#    def inherits(self, subclass_name, parent_name):
#        self.codegenerator.writeline("inherits(%s,%s);"%(subclass_name, parent_name))
    
    def throw(self): # Assumes the value to be thrown is on the stack.
        self.action(avm1.ActionThrow())
