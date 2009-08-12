
""" backend generator routines
"""

from pypy.translator.avm import avm1
from collections import namedtuple

Scope = namedtuple("Scope", "block parent callback stack")

def make_variable(name):
    if isinstance(name, Variable):
        return name
    return Variable(name)

class StackDummy(object):
    def __init__(self, name):
        self.name = name

class Variable(StackDummy):
    def __str__(self):
        return 'Variable(name="%s")' % self.name
    __repr__ = __str__

    def __add__(self, other):
        if isinstance(other, StackDummy):
            other = other.name
        return Variable("CONCAT %r %r" % (self.name, other))

    def __radd__(self, other):
        if isinstance(other, StackDummy):
            other = other.name
        return Variable("CONCAT %r %r" % (other, self.name))
        
    
class Function(StackDummy):
    pass

class AVM1Gen(object):
    """ AVM1 'assembler' generator routines """

    def __getattribute__(self, name):
        return object.__getattribute__(self, name)
    
    def __init__(self, block=None):
        self.block = block or avm1.Block(None, True)
        self.scope = Scope(self.block, None, None, [])
        self.action(self.block.constants)
        
    def new_label(self):
        return self.scope.block.new_label()

    def push_stack(self, *values):
        print "PUSHSTACK:", values
        for element in values:
            if isinstance(element, avm1.RegisterByIndex):
                element = Variable(self.scope.block.registers[element.index])
            elif isinstance(element, avm1.RegisterByValue):
                element = Variable(element.value)
            self.scope.stack.append(element)
    
    def pop_stack(self, n=1):
        v = [self.scope.stack.pop() for i in xrange(n)]
        print "POPSTACK:", v
        return v
    
    def store_register(self, name, index=-1):
        index = self.scope.block.store_register(name, index)
        self.action(avm1.ActionStoreRegister(index))
        return index
    
    def find_register(self, name):
        return self.scope.block.find_register(name)
    
    def action(self, action):
        return self.scope.block.add_action(action)
    
    def enter_scope(self, new_code_obj, exit_callback=None):
        self.scope = Scope(new_code_obj, self.scope, exit_callback, [])

    def in_function(self):
        return self.scope.block.FUNCTION_TYPE
    
    def exit_scope(self):
        block_len = self.finalize_block(self.scope.block)
        exit_callback = self.scope.callback
        
        # Go up to the parent scope.
        self.scope = self.scope.parent
        
        self.scope.block.current_offset += block_len
        if exit_callback is not None:
            exit_callback()

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
        self.enter_scope(self.action(avm1.ActionDefineFunction2(self.block, name, arglist)))
    
    def begin_prototype_method(self, function_name, _class, arglist):
        def exit_callback(block):
            self.set_member()
        self.push_const(function_name, "prototype", _class)
        self.get_variable()
        self.get_member()
        self.enter_scope(self.action(avm1.ActionDefineFunction2(self.block, "", arglist, 0)), exit_callback)
        self.push_stack(Function(function_name))

    def set_variable(self):
        value, name = self.pop_stack(2)
        print "SETVARIABLE: %r = %r" % (name, value)
        if isinstance(name, Variable):
            name = name.name
        assert isinstance(name, basestring)
        if self.find_register(name) >= 0:
            self.store_register(name)
        self.action(avm1.ActionSetVariable())
        
    def get_variable(self):
        name, = self.pop_stack()
        print "GETVARIABLE: %s" % (name,)
        self.action(avm1.ActionGetVariable())
        self.push_stack(make_variable(name))
    
    def set_member(self):
        self.action(avm1.ActionSetMember())
        self.pop_stack(3)

    def get_member(self):
        self.action(avm1.ActionGetMember())
        value, name, obj = self.pop_stack(3)
        print "GETMEMBER:", value, name, obj
        self.push_stack(Variable("%s.%s") % obj, name)
        
    def push_reg_index(self, index):
        self.push_const(avm1.RegisterByIndex(index))
    
    def push_arg(self, v):
        assert self.in_function() > 0, "avm1gen::push_arg called while not in function scope."
        self.push_local(v)
    
#    def push_value(self, v):
#        self.action(avm1.ActionPush(v.name))

    def push_var(self, v):
        k = self.find_register(v)
        if k >= 0:
            self.push_reg_index(k)
        else:
            self.push_const(v)
            self.get_variable()
            index = self.store_register(v)

    def push_this(self):
        self.push_var("this")
    
    def push_local(self, v):
        self.push_var(v.name)
        
    def push_const(self, *v):
        self.push_stack(*v)
        return self.action(avm1.ActionPush(v))

    def push_undefined(self):
        self.push_const(avm1.Undefined)

    def push_null(self):
        self.push_const(avm1.Null)
        
    def return_stmt(self):
        self.pop_stack()
        self.action(avm1.ActionReturn())

    def swap(self):
        a, b = self.pop_stack(2)
        self.push_stack(b, a)
        self.action(avm1.ActionSwap())
    
    def is_equal(self, value=None):
        if value is not None:
            self.push_const(value)
        self.action(avm1.ActionEquals())
        self.pop_stack(2)

    def is_not_equal(self, value=None):
        self.is_equal(value)
        self.action(avm1.ActionNot())
        self.pop_stack(2)
    
    def init_object(self, members=None):
        self.push_const(members.iteritems(), len(members))
        self.action(avm1.ActionInitObject())
        self.pop_stack(2)

    def init_array(self, members=None):
        self.push_const(members, len(members))
        self.pop_stack(2)
        self.action(avm1.ActionInitArray())

    # Assumes the args and number of args are on the stack.
    def call_function(self, func_name):
        self.push_const(func_name)
        self.action(avm1.ActionCallFunction())
        name, nargs = self.pop_stack()
        self.pop_stack(nargs)
        self.push_stack(Variable("%s_RETURN" % func_name))
    
    def call_function_constargs(self, func_name, *args):
        p = self.push_const(*reversed((func_name, len(args))+args))
        self.action(avm1.ActionCallFunction())
        self.pop_stack(2+len(args))
        self.push_stack(Variable("%s_RETURN" % func_name))
        
    # Assumes the args and number of args and ScriptObject are on the stack.
    def call_method(self, func_name):
        self.push_const(func_name)
        self.action(avm1.ActionCallMethod())
        name, obj, nargs = self.pop_stack(3)
        self.pop_stack(nargs)
        self.push_stack(Variable("%s.%s_RETURN" % (obj.name, name)))

    # Assumes the args and number of args are on the stack.
    def call_method_constvar(self, _class, func_name):
        self.push_var(_class)
        self.call_method()

    # Boolean value should be on stack when this is called
    def branch_if_true(self, label=""):
        if len(label) == 0:
            label = self.new_label()
        self.scope.block.branch_blocks[label] = avm1.Block(self.block, False)
        self.action(avm1.ActionIf(label))
        self.pop_stack()
        return (label, self.scope.block.branch_blocks[label])
    
    # Assumes the value is on the stack.
    def set_proto_field(self, objname, member_name):
        self.push_const("prototype")
        self.push_var(objname)
        self.get_member()
        self.swap()
        self.push_const(member_name)
        self.swap()
        self.set_member()

    # Assumes the value is on the stack.
    def set_static_field(self, objname, member_name):
        self.push_var(objname)
        self.swap()
        self.push_const(member_name)
        self.swap()
        self.set_member()

    # If no args are passed then it is assumed that the args and number of args are on the stack.
    def newobject_constthis(self, obj, *args):
        if len(args) > 0:
            self.push_const(args, len(args), obj)
        else:
            self.push_const(obj)
        self.newobject()
        
    
    def newobject(self):
        self.action(avm1.ActionNewObject())
        _, nargs = self.pop_stack()
        self.pop_stack(nargs)
        
    # FIXME: will refactor later
    #load_str = load_const
    
    def begin_switch_varname(self, varname):
        self.push_var(varname)
        self.switch_register = self.store_register(varname)
    
    def write_case(self, testee):
        self.push_const(avm1.RegisterByIndex(self.switch_register), testee)
        self.action(avm1.ActionStrictEquals())
        self.pop_stack(2)
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
    
    def throw(self): # Assumes the value to be thrown is on the stack.
        self.action(avm1.ActionThrow())
        self.pop_stack()

    def concat_string(self):
        self.action(avm1.ActionTypedAdd())
        self.push_stack(self.pop_stack()[0] + self.pop_stack()[0])
    
    #def extends(self):
    #    pass
        
