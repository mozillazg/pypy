import weakref
from pypy.lang.smalltalk import model, constants, utility, error
from pypy.tool.pairtype import extendabletype

class Invalidateable(object):
    def invalidate_shadow(self):
        pass

class AbstractShadow(Invalidateable):
    """A shadow is an optional extra bit of information that
    can be attached at run-time to any Smalltalk object.
    """
    
    def __init__(self, w_self, invalid):
        self._w_self = w_self
        self._notifyinvalid = []
        self.invalid = invalid
        self.w_invalid = False
        if invalid:
            self.invalidate_shadow()

    def notifyinvalid(self, other):
        self._notifyinvalid += [other]

    def unnotify(self, other):
        if other in self._notifyinvalid:
            self._notifyinvalid.remove(other)

    def getname(self):
        return repr(self)

    def invalidate_shadow(self):
        """XXX This should get called whenever the base Smalltalk
        object changes."""
        if not self.invalid:
            self.invalid = True
            for listener in self._notifyinvalid:
                listener.invalidate_shadow()
            self._notifyinvalid = []

    def invalidate_w_self(self):
        """XXX This should get called whenever the shadow
        object changes.
        (current shortcut, whenever the shadow is used)"""
        self.w_invalid = True

    def w_self(self):
        return self._w_self

    def sync_w_self(self):
        if self.w_invalid:
            self.update_w_self()

    def sync_shadow(self):
        if self.invalid:
            self.update_shadow()

    def update_shadow(self):
        self.w_self().setshadow(self)
        self.invalid = False

    def update_w_self(self):
        self.w_invalid = False

# ____________________________________________________________ 

POINTERS = 0
BYTES = 1
WORDS = 2
WEAK_POINTERS = 3
COMPILED_METHOD = 4


class MethodNotFound(error.SmalltalkException):
    pass

class ClassShadowError(error.SmalltalkException):
    pass

class ClassShadow(AbstractShadow):
    """A shadow for Smalltalk objects that are classes
    (i.e. used as the class of another Smalltalk object).
    """
    def __init__(self, w_self, invalid):
        AbstractShadow.__init__(self, w_self, invalid)

    def invalidate_shadow(self):
        AbstractShadow.invalidate_shadow(self)
        self.methoddict = {}
        self.s_superclass = None     # the ClassShadow of the super class
        self.name = None

    def getname(self):
        return "%s class" % (self.name or '?',)

    def update_shadow(self):
        from pypy.lang.smalltalk import objtable

        "Update the ClassShadow with data from the w_self class."
        AbstractShadow.update_shadow(self)

        w_self = self.w_self()
        # read and painfully decode the format
        classformat = utility.unwrap_int(
            w_self._vars[constants.CLASS_FORMAT_INDEX])
        # The classformat in Squeak, as an integer value, is:
        #    <2 bits=instSize//64><5 bits=cClass><4 bits=instSpec>
        #                                    <6 bits=instSize\\64><1 bit=0>
        # In Slang the value is read directly as a boxed integer, so that
        # the code gets a "pointer" whose bits are set as above, but
        # shifted one bit to the left and with the lowest bit set to 1.

        # compute the instance size (really the size, not the number of bytes)
        instsize_lo = (classformat >> 1) & 0x3F
        instsize_hi = (classformat >> (9 + 1)) & 0xC0
        self.instance_size = (instsize_lo | instsize_hi) - 1  # subtract hdr
        # decode the instSpec
        format = (classformat >> 7) & 15
        self.instance_varsized = format >= 2
        if format < 4:
            self.instance_kind = POINTERS
        elif format == 4:
            self.instance_kind = WEAK_POINTERS
        elif format == 6:
            self.instance_kind = WORDS
            if self.instance_size != 0:
                raise ClassShadowError("can't have both words and a non-zero "
                                       "base instance size")
        elif 8 <= format <= 11:
            self.instance_kind = BYTES
            if self.instance_size != 0:
                raise ClassShadowError("can't have both bytes and a non-zero "
                                       "base instance size")
        elif 12 <= format <= 15:
            self.instance_kind = COMPILED_METHOD
        else:
            raise ClassShadowError("unknown format %d" % (format,))
        # read the name
        if w_self.size() > constants.CLASS_NAME_INDEX:
            w_name = w_self._vars[constants.CLASS_NAME_INDEX]
        else:
            w_name = None

        # XXX This is highly experimental XXX
        # if the name-pos of class is not bytesobject,
        # we are probably holding a metaclass instead of a class.
        # metaclasses hold a pointer to the real class in the last
        # slot. This is pos 6 in mini.image and higher in squeak3.9
        if w_name is None:
            w_realclass = w_self._vars[w_self.size() - 1]
            assert isinstance(w_realclass, model.W_PointersObject)
            if w_realclass.size() > constants.CLASS_NAME_INDEX:
                w_name = w_realclass._vars[constants.CLASS_NAME_INDEX]
        if isinstance(w_name, model.W_BytesObject):
            self.name = w_name.as_string()
        # read the methoddict
        w_methoddict = w_self._vars[constants.CLASS_METHODDICT_INDEX]
        assert isinstance(w_methoddict, model.W_PointersObject)
        s_methoddict = w_methoddict.as_methoddict_get_shadow()
        self.methoddict = s_methoddict.methoddict
        s_methoddict.notifyinvalid(self)

        # for the rest, we need to reset invalid to False already so
        # that cycles in the superclass and/or metaclass chains don't
        # cause infinite recursion
        # read s_superclass
        w_superclass = w_self._vars[constants.CLASS_SUPERCLASS_INDEX]
        if w_superclass is not objtable.w_nil:
            assert isinstance(w_superclass, model.W_PointersObject)
            self.s_superclass = w_superclass.as_class_get_shadow()
            self.s_superclass.notifyinvalid(self)
        AbstractShadow.update_shadow(self)

    # XXX check better way to store objects
    # XXX storing is necessary for "become" which loops over all pointers
    # XXX and replaces old pointers with new pointers
    def new(self, extrasize=0, store=True):
        from pypy.lang.smalltalk import classtable
        w_cls = self.w_self()
        if self.instance_kind == POINTERS:
            w_new = model.W_PointersObject(w_cls, self.instance_size+extrasize)
        elif self.instance_kind == WORDS:
            w_new = model.W_WordsObject(w_cls, extrasize)
        elif self.instance_kind == BYTES:
            w_new = model.W_BytesObject(w_cls, extrasize)
        elif self.instance_kind == COMPILED_METHOD:
            w_new = model.W_CompiledMethod(extrasize)
        else:
            raise NotImplementedError(self.instance_kind)
        # XXX Used for non-PyPy way of doing become.
        if store:
            from pypy.lang.smalltalk import objtable
            objtable.objects.extend([w_new])
        return w_new

    # _______________________________________________________________
    # Methods for querying the format word, taken from the blue book:
    #
    # included so that we can reproduce code from the reference impl
    # more easily

    def ispointers(self):
        " True if instances of this class have data stored as pointers "
        XXX   # what about weak pointers?
        return self.format == POINTERS

    def iswords(self):
        " True if instances of this class have data stored as numerical words "
        XXX   # what about weak pointers?
        return self.format in (POINTERS, WORDS)

    def isbytes(self):
        " True if instances of this class have data stored as numerical bytes "
        return self.format == BYTES

    def isvariable(self):
        " True if instances of this class have indexed inst variables "
        return self.instance_varsized

    def instsize(self):
        " Number of named instance variables for each instance of this class "
        return self.instance_size

    def inherits_from(self, s_superclass):
        classshadow = self
        while classshadow is not None:
            if classshadow is s_superclass:
                return True
            classshadow = classshadow.s_superclass
        else:
            return False

    # _______________________________________________________________
    # Methods for querying the format word, taken from the blue book:

    def __repr__(self):
        return "<ClassShadow %s>" % (self.name or '?',)

    def lookup(self, selector):
        look_in_shadow = self
        while look_in_shadow is not None:
            try:
                w_method = look_in_shadow.methoddict[selector]
                # We locally cache the method we found.
                #if look_in_shadow is not self:
                #    self.methoddict[selector] = w_method
                return w_method
            except KeyError, e:
                look_in_shadow = look_in_shadow.s_superclass
        raise MethodNotFound(self, selector)

    def installmethod(self, selector, method):
        "NOT_RPYTHON"     # this is only for testing.
        assert isinstance(method, model.W_CompiledMethod)
        self.methoddict[selector] = method
        method.w_compiledin = self.w_self()

class MethodDictionaryShadow(AbstractShadow):
    def __init__(self, w_self, invalid):
        AbstractShadow.__init__(self, w_self, invalid)

    def invalidate_shadow(self):
        self.methoddict = {}

    def update_shadow(self):
        from pypy.lang.smalltalk import objtable
        w_values = self.w_self()._vars[constants.METHODDICT_VALUES_INDEX]
        assert isinstance(w_values, model.W_PointersObject)
        s_values = w_values.get_shadow()
        s_values.notifyinvalid(self)
        size = self.w_self().size() - constants.METHODDICT_NAMES_INDEX
        for i in range(size):
            w_selector = self.w_self()._vars[constants.METHODDICT_NAMES_INDEX+i]
            if w_selector is not objtable.w_nil:
                if not isinstance(w_selector, model.W_BytesObject):
                    raise ClassShadowError("bogus selector in method dict")
                selector = w_selector.as_string()
                w_compiledmethod = w_values._vars[i]
                if not isinstance(w_compiledmethod, model.W_CompiledMethod):
                    raise ClassShadowError("the methoddict must contain "
                                           "CompiledMethods only for now")
                self.methoddict[selector] = w_compiledmethod

class LinkedListShadow(AbstractShadow):
    def __init__(self, w_self, invalid):
        AbstractShadow.__init__(self, w_self, invalid)

    def w_firstlink(self):
        w_v = self.w_self()._vars[constants.FIRST_LINK_INDEX]
        assert isinstance(w_v, model.W_PointersObject)
        return w_v

    def store_w_firstlink(self, w_object):
        self.w_self()._vars[constants.FIRST_LINK_INDEX] = w_object

    def w_lastlink(self):
        w_v = self.w_self()._vars[constants.LAST_LINK_INDEX]
        assert isinstance(w_v, model.W_PointersObject)
        return w_v

    def store_w_lastlink(self, w_object):
        self.w_self()._vars[constants.LAST_LINK_INDEX] = w_object

    def is_empty_list(self):
        from pypy.lang.smalltalk import objtable
        return self.w_firstlink() == objtable.w_nil

    def add_last_link(self, w_object):
        if self.is_empty_list():
            self.store_w_firstlink(w_object)
        else:
            self.w_lastlink().as_link_get_shadow().store_next(w_object)
        # XXX Slang version stores list in process here...
        self.store_w_lastlink(w_object)

    def remove_first_link_of_list(self):
        from pypy.lang.smalltalk import objtable
        first = self.w_firstlink()
        last = self.w_lastlink()
        if first == last:
            self.store_w_firstlink(objtable.w_nil)
            self.store_w_lastlink(objtable.w_nil)
        else:
            next = first.as_process_get_shadow().next()
            self.store_w_firstlink(next)
        first.as_process_get_shadow().store_next(objtable.w_nil)
        return first

class SemaphoreShadow(LinkedListShadow):
    """A shadow for Smalltalk objects that are semaphores
    """
    def __init__(self, w_self, invalid=False):
        LinkedListShadow.__init__(self, w_self, invalid)

    def put_to_sleep(self, s_process):
        priority = s_process.priority()
        s_scheduler = self.s_scheduler()
        w_process_lists = s_scheduler.process_lists()
        w_process_list = w_process_lists._vars[priority]
        assert isinstance(w_process_list, model.W_PointersObject)
        w_process_list.as_linkedlist_get_shadow().add_last_link(s_process.w_self())
        s_process.store_my_list(w_process_list)
        
    def transfer_to(self, s_process, interp):
        from pypy.lang.smalltalk import objtable
        s_scheduler = self.s_scheduler()
        s_old_process = s_scheduler.s_active_process()
        s_scheduler.store_w_active_process(s_process.w_self())
        s_old_process.store_w_suspended_context(interp.s_active_context().w_self())
        interp.store_w_active_context(s_process.w_suspended_context())
        s_process.store_w_suspended_context(objtable.w_nil)
        #reclaimableContextCount := 0

    def s_scheduler(self):
        from pypy.lang.smalltalk import objtable
        w_association = objtable.objtable["w_schedulerassociationpointer"]
        assert w_association is not None
        assert isinstance(w_association, model.W_PointersObject)
        w_scheduler = w_association.as_association_get_shadow().value()
        assert isinstance(w_scheduler, model.W_PointersObject)
        return w_scheduler.as_scheduler_get_shadow()

    def resume(self, w_process, interp):
        s_process = w_process.as_process_get_shadow()
        s_scheduler = self.s_scheduler()
        s_active_process = s_scheduler.s_active_process()
        active_priority = s_active_process.priority()
        new_priority = s_process.priority()
        if new_priority > active_priority:
            self.put_to_sleep(s_active_process)
            self.transfer_to(s_process, interp)
        else:
            self.put_to_sleep(s_process)

    def synchronous_signal(self, interp):
        if self.is_empty_list():
            w_value = self.w_self()._vars[constants.EXCESS_SIGNALS_INDEX]
            w_value = utility.wrap_int(utility.unwrap_int(w_value) + 1)
            self.w_self()._vars[constants.EXCESS_SIGNALS_INDEX] = w_value
        else:
            self.resume(self.remove_first_link_of_list(), interp)

class LinkShadow(AbstractShadow):
    def __init__(self, w_self, invalid):
        AbstractShadow.__init__(self, w_self, invalid)

    def next(self):
        return self.w_self()._vars[constants.NEXT_LINK_INDEX]

    def store_next(self, w_object):
        self.w_self()._vars[constants.NEXT_LINK_INDEX] = w_object

class ProcessShadow(LinkShadow):
    """A shadow for Smalltalk objects that are processes
    """
    def __init__(self, w_self, invalid):
        LinkShadow.__init__(self, w_self, invalid)

    def priority(self):
        return utility.unwrap_int(self.w_self()._vars[constants.PROCESS_PRIORITY_INDEX])

    def my_list(self):
        return self.w_self()._vars[constants.PROCESS_MY_LIST_INDEX]

    def store_my_list(self, w_object):
        self.w_self()._vars[constants.PROCESS_MY_LIST_INDEX] = w_object

    def w_suspended_context(self):
        # XXX Can currently only restart context if it is a method context...
        # XXX Depends on typechecking ...
        return self.w_self()._vars[constants.PROCESS_SUSPENDED_CONTEXT_INDEX]

    def store_w_suspended_context(self, w_object):
        self.w_self()._vars[constants.PROCESS_SUSPENDED_CONTEXT_INDEX] = w_object

class AssociationShadow(AbstractShadow):
    def __init__(self, w_self, invalid):
        AbstractShadow.__init__(self, w_self, invalid)

    def key(self):
        return self.w_self()._vars[constants.ASSOCIATION_KEY_INDEX]

    def value(self):
        return self.w_self()._vars[constants.ASSOCIATION_VALUE_INDEX]

    def store_value(self, w_value):
        self.w_self()._vars[constants.ASSOCIATION_VALUE_INDEX] = w_value

class SchedulerShadow(AbstractShadow):
    def __init__(self, w_self, invalid):
        AbstractShadow.__init__(self, w_self, invalid)

    def s_active_process(self):
        w_v = self.w_self()._vars[constants.SCHEDULER_ACTIVE_PROCESS_INDEX]
        assert isinstance(w_v, model.W_PointersObject)
        return w_v.as_process_get_shadow()

    def store_w_active_process(self, w_object):
        self.w_self()._vars[constants.SCHEDULER_ACTIVE_PROCESS_INDEX] = w_object
    
    def process_lists(self):
        w_v = self.w_self()._vars[constants.SCHEDULER_PROCESS_LISTS_INDEX]
        assert isinstance(w_v, model.W_PointersObject)
        return w_v

class ContextPartShadow(AbstractShadow):

    __metaclass__ = extendabletype

    def update_shadow(self):
        AbstractShadow.update_shadow(self)
        self._stack = [self.w_self()._vars[i]
                        for i in range(self.stackstart(),
                                       self.stackpointer())]
        self.init_pc()
        # Using a shadow most likely results in an invalid state for w_self
        self.invalidate_w_self()

    def init_pc(self):
        self._pc = utility.unwrap_int(self.w_self()._vars[constants.CTXPART_PC_INDEX])
        self._pc -= self.w_method().bytecodeoffset()
        self._pc -= 1

    def save_back_pc(self):
        pc = self._pc
        pc += 1
        pc += self.w_method().bytecodeoffset()
        self.w_self()._vars[constants.CTXPART_PC_INDEX] = utility.wrap_int(pc)

    def update_w_self(self):
        AbstractShadow.update_w_self(self)
        for i in range(len(self._stack)):
            self.w_self()._vars[self.stackstart() + i] = self._stack[i]
        self.store_stackpointer(len(self._stack))
        self.save_back_pc()

    def __init__(self, w_self, invalid):
        AbstractShadow.__init__(self, w_self, invalid)

    def w_home(self):
        raise NotImplementedError()

    def s_home(self):
        raise NotImplementedError()
    
    def stackstart(self):
        raise NotImplementedError()

    def stackpointer_offset(self):
        raise NotImplementedError()

    def w_receiver(self):
        " Return self of the method, or the method that contains the block "
        return self.s_home().w_receiver()

    def w_sender(self):
        w_v = self.w_self()._vars[constants.CTXPART_SENDER_INDEX]
        assert isinstance(w_v, model.W_PointersObject)
        return w_v

    def s_sender(self):
        from pypy.lang.smalltalk import objtable
        w_sender = self.w_sender()
        if w_sender == objtable.w_nil:
            return None
        else:
            return w_sender.as_context_get_shadow()

    def store_w_sender(self, w_sender):
        self.w_self()._vars[constants.CTXPART_SENDER_INDEX] = w_sender

    def pc(self):
        return self._pc

    def store_pc(self, newpc):
        self._pc = newpc

    def stackpointer(self):
        return (utility.unwrap_int(self.w_self()._vars[constants.CTXPART_STACKP_INDEX]) +
                self.stackpointer_offset())

    def stackpointer_offset(self):
        raise NotImplementedError()

    def store_stackpointer(self, pointer):
        self.w_self()._vars[constants.CTXPART_STACKP_INDEX] = utility.wrap_int(pointer)

    # ______________________________________________________________________
    # Method that contains the bytecode for this method/block context

    def w_method(self):
        return self.s_home().w_method()

    def getbytecode(self):
        assert self._pc >= 0
        bytecode = self.w_method().bytes[self._pc]
        currentBytecode = ord(bytecode)
        self._pc += 1
        return currentBytecode

    def getNextBytecode(self):
        self.currentBytecode = self.getbytecode()
        return self.currentBytecode

    # ______________________________________________________________________
    # Temporary Variables
    #
    # Are always fetched relative to the home method context.
    
    def gettemp(self, index):
        return self.s_home().gettemp(index)

    def settemp(self, index, w_value):
        self.s_home().settemp(index, w_value)

    # ______________________________________________________________________
    # Stack Manipulation
    def pop(self):
        w_v = self._stack[-1]
        self._stack = self._stack[:-1]
        return w_v

    def push(self, w_v):
        self._stack += [w_v]

    def push_all(self, lst):
        #for x in lst:
        #    self.push(x)
        self._stack += lst

    def top(self):
        return self.peek(0)
        
    def peek(self, idx):
        return self._stack[-(idx + 1)]

    def pop_n(self, n):
        assert n >= 0
        start = len(self._stack) - n
        assert start >= 0          # XXX what if this fails?
        del self._stack[start:]

    def stack(self):
        return self._stack

    def pop_and_return_n(self, n):
        assert n >= 0
        start = len(self._stack) - n
        assert start >= 0          # XXX what if this fails?
        res = self._stack[start:]
        del self._stack[start:]
        return res

class BlockContextShadow(ContextPartShadow):

    def __init__(self, w_self, invalid):
        self._s_home = None
        ContextPartShadow.__init__(self, w_self, invalid)

    def invalidate_shadow(self):
        if self._s_home is not None:
            self._s_home.unnotify(self)
            self._s_home = None
        AbstractShadow.invalidate_shadow(self)

    def update_shadow(self):
        self.store_w_home(self.w_self()._vars[constants.BLKCTX_HOME_INDEX])
        self._initialip = utility.unwrap_int(self.w_self()._vars[constants.BLKCTX_INITIAL_IP_INDEX])
        self._initialip -= 1 + self.w_method().getliteralsize()
        self._eargc = utility.unwrap_int(self.w_self()._vars[constants.BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX])
        ContextPartShadow.update_shadow(self)

    def update_w_self(self):
        ContextPartShadow.update_w_self(self)
        self.w_self()._vars[constants.BLKCTX_INITIAL_IP_INDEX] = utility.wrap_int(self._initialip + 1 + self.w_method().getliteralsize())
        self.w_self()._vars[constants.BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX] = utility.wrap_int(self._eargc)
        self.w_self()._vars[constants.BLKCTX_HOME_INDEX] = self._w_home

    def expected_argument_count(self):
        return self._eargc

    def store_expected_argument_count(self, argc):
        self._eargc = argc

    def initialip(self):
        return self._initialip
        
    def store_initialip(self, initialip):
        self._initialip = initialip
        
    def store_w_home(self, w_home):
        if self._s_home is not None:
            self._s_home.unnotify(self)
            self._s_home = None
        assert isinstance(w_home, model.W_PointersObject)
        self._w_home = w_home

    def w_home(self):
        return self._w_home

    def s_home(self):
        if self._s_home is None:
            self._s_home = self._w_home.as_methodcontext_get_shadow()
            self._s_home.notifyinvalid(self)
        return self._s_home

    def reset_stack(self):
        self._stack = []

    def stackstart(self):
        return constants.BLKCTX_STACK_START

    def stackpointer_offset(self):
        return constants.BLKCTX_STACK_START

class MethodContextShadow(ContextPartShadow):
    def __init__(self, w_self, invalid):
        ContextPartShadow.__init__(self, w_self, invalid)

    def update_shadow(self):
        # Make sure the method is updated first
        self.store_w_method(self.w_self()._vars[constants.MTHDCTX_METHOD])
        ContextPartShadow.update_shadow(self)

    def update_w_self(self):
        ContextPartShadow.update_w_self(self)
        self.w_self()._vars[constants.MTHDCTX_METHOD] = self._w_method

    def w_method(self):
        return self._w_method

    def store_w_method(self, w_method):
        assert isinstance(w_method, model.W_CompiledMethod)
        self._w_method = w_method

    def w_receiver(self):
        return self.w_self()._vars[constants.MTHDCTX_RECEIVER]

    def store_w_receiver(self, w_receiver):
        self.w_self()._vars[constants.MTHDCTX_RECEIVER] = w_receiver

    def gettemp(self, index0):
        return self.w_self()._vars[constants.MTHDCTX_TEMP_FRAME_START + index0]

    def settemp(self, index0, w_value):
        self.w_self()._vars[constants.MTHDCTX_TEMP_FRAME_START + index0] = w_value

    def w_home(self):
        return self.w_self()

    def s_home(self):
        return self

    def store_stackpointer(self, pointer):
        ContextPartShadow.store_stackpointer(self,
                                             pointer+self.w_method().tempframesize())

    def stackpointer_offset(self):
        return constants.MTHDCTX_TEMP_FRAME_START

    def stackstart(self):
        w_method = self.w_method()
        return (constants.MTHDCTX_TEMP_FRAME_START +
                w_method.tempframesize())
