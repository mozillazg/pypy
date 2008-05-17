from pypy.lang.smalltalk import model

class Wrapper(object):
    def __init__(self, w_self):
        assert isinstance(w_self, model.W_PointersObject)
        self.w_self = w_self

    def read(self, index0):
        try:
            return self.w_self._vars[index0]
        except IndexError:
            # XXX nicer errormessage
            raise

    def write(self, index0, w_new):
        try:
            self.w_self._vars[index0] = w_new
        except IndexError:
            # XXX nicer errormessage
            raise
    

'''class LinkedListShadow(AbstractShadow):
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

'''
