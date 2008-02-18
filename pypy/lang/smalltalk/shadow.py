import weakref
from pypy.lang.smalltalk import model, constants, utility, error

class AbstractShadow(object):
    """A shadow is an optional extra bit of information that
    can be attached at run-time to any Smalltalk object.
    """
    def invalidate(self):
        """XXX This should get called whenever the base Smalltalk
        object changes."""

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
    def __init__(self, w_self):
        self.w_self = w_self
        self.invalidate()

    def invalidate(self):
        self.methoddict = {}
        self.s_superclass = None     # the ClassShadow of the super class
        self.name = None
        self.invalid = True

    def check_for_updates(self):
        if self.invalid:
            self.update_shadow()

    def update_shadow(self):
        from pypy.lang.smalltalk import objtable

        "Update the ClassShadow with data from the w_self class."

        w_self = self.w_self
        # read and painfully decode the format
        classformat = utility.unwrap_int(
            w_self.fetch(constants.CLASS_FORMAT_INDEX))
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
            w_name = w_self.fetch(constants.CLASS_NAME_INDEX)

        # XXX This is highly experimental XXX
        # if the name-pos of class is not bytesobject,
        # we are probably holding a metaclass instead of a class.
        # metaclasses hold a pointer to the real class in the last
        # slot. This is pos 6 in mini.image and higher in squeak3.9
        if not isinstance(w_name, model.W_BytesObject):
            w_realclass = w_self.fetch(w_self.size() - 1)
            if w_realclass.size() > constants.CLASS_NAME_INDEX:
                w_name = w_realclass.fetch(constants.CLASS_NAME_INDEX)
        if isinstance(w_name, model.W_BytesObject):
            self.name = w_name.as_string()
        # read the methoddict
        w_methoddict = w_self.fetch(constants.CLASS_METHODDICT_INDEX)
        w_values = w_methoddict.fetch(constants.METHODDICT_VALUES_INDEX)
        size = w_methoddict.size() - constants.METHODDICT_NAMES_INDEX
        for i in range(size):
            w_selector = w_methoddict.fetch(constants.METHODDICT_NAMES_INDEX+i)
            if w_selector is not objtable.w_nil:
                if not isinstance(w_selector, model.W_BytesObject):
                    raise ClassShadowError("bogus selector in method dict")
                selector = w_selector.as_string()
                w_compiledmethod = w_values.fetch(i)
                if not isinstance(w_compiledmethod, model.W_CompiledMethod):
                    raise ClassShadowError("the methoddict must contain "
                                           "CompiledMethods only for now")
                self.methoddict[selector] = w_compiledmethod
        # for the rest, we need to reset invalid to False already so
        # that cycles in the superclass and/or metaclass chains don't
        # cause infinite recursion
        self.invalid = False
        # read s_superclass
        w_superclass = w_self.fetch(constants.CLASS_SUPERCLASS_INDEX)
        if w_superclass is objtable.w_nil:
            self.s_superclass = None
        else:
            self.s_superclass = w_superclass.as_class_get_shadow()

    def new(self, extrasize=0):
        from pypy.lang.smalltalk import classtable
        w_cls = self.w_self
        
        if w_cls == classtable.w_BlockContext:
            return model.W_BlockContext(None, None, 0, 0)
        elif w_cls == classtable.w_MethodContext:
            # From slang: Contexts must only be created with newForMethod:
            # raise error.PrimitiveFailedError
            # XXX XXX XXX XXX
            # The above text is bogous. This does not come from slang but a
            # method implementation of ContextPart in Squeak3.9 which
            # overwrites the default compiledmethod to give this error.
            # The mini.image -however- doesn't overwrite this method, and as
            # far as I was able to trace it back, it -does- call this method.
            from pypy.rlib.objectmodel import instantiate
            return instantiate(model.W_MethodContext)
            
        if self.instance_kind == POINTERS:
            return model.W_PointersObject(w_cls, self.instance_size+extrasize)
        elif self.instance_kind == WORDS:
            return model.W_WordsObject(w_cls, extrasize)
        elif self.instance_kind == BYTES:
            return model.W_BytesObject(w_cls, extrasize)
        elif self.instance_kind == COMPILED_METHOD:
            return model.W_CompiledMethod(extrasize)
        else:
            raise NotImplementedError(self.instance_kind)

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
        while True:
            try:
                return look_in_shadow.methoddict[selector]
            except KeyError:
                pass
            look_in_shadow = look_in_shadow.s_superclass
            if look_in_shadow is None:
                # attach information on the exception, for debugging.
                raise MethodNotFound(self, selector)

    def installmethod(self, selector, method):
        "NOT_RPYTHON"     # this is only for testing.
        assert isinstance(method, model.W_CompiledMethod)
        self.methoddict[selector] = method
        method.w_compiledin = self.w_self

class LinkedListShadow(AbstractShadow):
    def __init__(self, w_self):
        self.w_self = w_self

    def firstlink(self):
        return self.w_self.at0(constants.FIRST_LINK_INDEX)

    def store_firstlink(self, w_object):
        return self.w_self.atput0(constants.FIRST_LINK_INDEX, w_object)

    def lastlink(self):
        return self.w_self.at0(constants.LAST_LINK_INDEX)

    def store_lastlink(self, w_object):
        return self.w_self.atput0(constants.LAST_LINK_INDEX, w_object)

    def is_empty_list(self):
        from pypy.lang.smalltalk import objtable
        return self.firstlink() == objtable.w_nil

    def add_last_link(self, w_object):
        if self.is_empty_list():
            self.store_firstlink(w_object)
        else:
            self.lastlink().store_next(w_object)
        # XXX Slang version stores list in process here...
        self.store_lastlink(w_object)

    def remove_first_link_of_list(self):
        from pypy.lang.smalltalk import objtable
        first = self.firstlink()
        last = self.lastlink()
        if first == last:
            self.store_firstlink(objtable.w_nil)
            self.store_lastlink(objtable.w_nil)
        else:
            next = first.as_process_get_shadow().next()
            self.store_firstlink(next)
        first.as_process_get_shadow().store_next(objtable.w_nil)
        return first

class SemaphoreShadow(LinkedListShadow):
    """A shadow for Smalltalk objects that are semaphores
    """
    def __init__(self, w_self):
        self.w_self = w_self

    def put_to_sleep(self, s_process):
        priority = s_process.priority()
        s_scheduler = self.scheduler()
        w_process_lists = s_scheduler.process_lists()
        w_process_list = w_process_lists.at0(priority)
        w_process_list.as_linkedlist_get_shadow().add_last_link(s_process.w_self)
        s_process.store_my_list(w_process_list)
        
    def transfer_to(self, s_process, interp):
        from pypy.lang.smalltalk import objtable
        s_scheduler = self.scheduler()
        s_old_process = s_scheduler.active_process()
        s_scheduler.store_active_process(s_process)
        s_old_process.store_suspended_context(interp.w_active_context)
        interp.w_active_context = s_process.suspended_context()
        s_process.store_suspended_context(objtable.w_nil)
        #reclaimableContextCount := 0

    def scheduler(self):
        from pypy.lang.smalltalk import objtable
        w_association = objtable.objtable["w_schedulerassociationpointer"]
        w_scheduler = w_association.as_association_get_shadow().value()
        return w_scheduler.as_scheduler_get_shadow()

    def resume(self, w_process, interp):
        s_process = w_process.as_process_get_shadow()
        s_scheduler = self.scheduler()
        s_active_process = s_scheduler.active_process()
        active_priority = s_active_process.priority()
        new_priority = s_process.priority()
        if new_priority > active_priority:
            self.put_to_sleep(s_active_process)
            self.transfer_to(s_process, interp)
        else:
            self.put_to_sleep(s_process)

    def synchronous_signal(self, interp):
        print "SYNCHRONOUS SIGNAL"
        if self.is_empty_list():
            w_value = self.w_self.at0(constants.EXCESS_SIGNALS_INDEX)
            w_value = utility.wrap_int(utility.unwrap_int(w_value) + 1)
            self.w_self.atput0(constants.EXCESS_SIGNALS_INDEX, w_value)
        else:
            self.resume(self.remove_first_link_of_list(), interp)

class LinkShadow(AbstractShadow):
    def __init__(self, w_self):
        self.w_self = self

    def next(self):
        return self.w_self.at0(constants.NEXT_LINK_INDEX)

    def store_next(self, w_object):
        self.w_self.atput0(constants.NEXT_LINK_INDEX, w_object)

class ProcessShadow(LinkShadow):
    """A shadow for Smalltalk objects that are processes
    """
    def __init__(self, w_self):
        self.w_self = w_self

    def priority(self):
        return utility.unwrap_int(self.w_self.at0(constants.PROCESS_PRIORITY_INDEX))

    def my_list(self):
        return self.w_self.at0(constants.PROCESS_MY_LIST_INDEX)

    def store_my_list(self, w_object):
        self.w_self.atput0(constants.PROCESS_MY_LIST_INDEX, w_object)

    def suspended_context(self):
        return self.w_self.at0(constants.PROCESS_SUSPENDED_CONTEXT_INDEX)

    def store_suspended_context(self, w_object):
        self.w_self.atput0(constants.PROCESS_SUSPENDED_CONTEXT_INDEX, w_object)

class AssociationShadow(AbstractShadow):
    def __init__(self, w_self):
        self.w_self = w_self

    def key(self):
        return self.w_self.at0(constants.ASSOCIATION_KEY_INDEX)

    def value(self):
        return self.w_self.at0(constants.ASSOCIATION_VALUE_INDEX)

class SchedulerShadow(AbstractShadow):
    def __init__(self, w_self):
        self.w_self = w_self

    def active_process(self):
        return self.w_self.at0(constants.SCHEDULER_ACTIVE_PROCESS_INDEX).as_process_get_shadow()

    def store_active_process(self, w_object):
        self.w_self.atput0(constants.SCHEDULER_ACTIVE_PROCESS_INDEX, w_object)
    
    def process_lists(self):
        return self.w_self.at0(constants.SCHEDULER_PROCESS_LISTS_INDEX)
