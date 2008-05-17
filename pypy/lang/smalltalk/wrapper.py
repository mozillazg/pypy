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

def make_getter(index0):
    def getter(self):
        return self.read(index0)
    return getter

def make_setter(index0):
    def setter(self, w_new):
        return self.write(index0, w_new)
    return setter

def make_getter_setter(index0):
    return make_getter(index0), make_setter(index0)
    
class LinkWrapper(Wrapper):
    next_link, store_next_link = make_getter_setter(0)

class ProcessWrapper(LinkWrapper):
    suspended_context, store_suspended_context = make_getter_setter(1)
    priority = make_getter(2)
    my_list, store_my_list = make_getter_setter(3)

class LinkedListWrapper(Wrapper):
    first_link, store_first_link = make_getter_setter(0)
    last_link, store_last_link = make_getter_setter(1)

    def is_empty_list(self):
        from pypy.lang.smalltalk import objtable
        return self.first_link() is objtable.w_nil

    def add_last_link(self, w_object):
        if self.is_empty_list():
            self.store_first_link(w_object)
        else:
            LinkWrapper(self.last_link()).store_next_link(w_object)
        self.store_last_link(w_object)

    def remove_first_link_of_list(self):
        from pypy.lang.smalltalk import objtable
        w_first = self.first_link()
        w_last = self.last_link()
        if w_first is w_last:
            self.store_first_link(objtable.w_nil)
            self.store_last_link(objtable.w_nil)
        else:
            w_next = LinkWrapper(w_first).next_link()
            self.store_first_link(w_next)
        LinkWrapper(w_first).store_next_link(objtable.w_nil)
        return w_first

class AssociationWrapper(Wrapper):
    key = make_getter(0)
    value, store_value = make_getter_setter(1)

'''
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



class SemaphoreWrapper(LinkedListWrapper):

    excess_signals, store_excess_signals = make_getter_setter(0)

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
        process = ProcessWrapper(w_process)
        scheduler = self.scheduler()
        active_process = scheduler.s_active_process()
        active_priority = active_process.priority()
        new_priority = process.priority()
        if new_priority > active_priority:
            self.put_to_sleep(active_process)
            self.transfer_to(process, interp)
        else:
            self.put_to_sleep(process)

    def synchronous_signal(self, interp):
        if self.is_empty_list():
            w_value = self.excess_signals()
            w_value = utility.wrap_int(utility.unwrap_int(w_value) + 1)
            self.store_excess_signals(w_value)
        else:
            self.resume(self.remove_first_link_of_list(), interp)

'''

