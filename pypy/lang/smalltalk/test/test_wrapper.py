import py
from pypy.lang.smalltalk import wrapper
from pypy.lang.smalltalk import model
from pypy.lang.smalltalk import objtable, utility
from pypy.lang.smalltalk import interpreter

def test_simpleread():
    w_o = model.W_PointersObject(None, 2)
    w = wrapper.Wrapper(w_o)
    w_o._vars[0] = "hello"
    assert w.read(0) == "hello"
    w.write(1, "b")
    assert w.read(1) == "b"
    py.test.raises(IndexError, "w.read(2)")
    py.test.raises(IndexError, "w.write(2, \"test\")")

def test_accessor_generators():
    w_o = model.W_PointersObject(None, 1)
    w = wrapper.LinkWrapper(w_o)
    w_o._vars[0] = "hello"
    assert w.next_link() == "hello"
    w.store_next_link("boe")
    assert w.next_link() == "boe"

def link(w_next='foo'):
    w_object = model.W_PointersObject(None, 1)
    wrapper.LinkWrapper(w_object).store_next_link(w_next)
    return w_object

def test_linked_list():
    w_object = model.W_PointersObject(None,2)
    w_last = link(objtable.w_nil)
    w_lb1 = link(w_last)
    w_lb2 = link(w_lb1)
    w_lb3 = link(w_lb2)
    w_lb4 = link(w_lb3)
    w_first = link(w_lb4)
    linkedlist = wrapper.LinkedListWrapper(w_object)
    linkedlist.store_first_link(w_first)
    linkedlist.store_last_link(w_last)
    assert w_first is linkedlist.first_link()
    assert w_last is linkedlist.last_link()
    assert linkedlist.remove_first_link_of_list() is w_first
    assert linkedlist.remove_first_link_of_list() is w_lb4
    assert linkedlist.remove_first_link_of_list() is w_lb3
    assert not linkedlist.is_empty_list()
    assert linkedlist.remove_first_link_of_list() is w_lb2
    assert linkedlist.remove_first_link_of_list() is w_lb1
    assert linkedlist.remove_first_link_of_list() is w_last
    assert linkedlist.is_empty_list()
    linkedlist.add_last_link(w_first)
    assert linkedlist.first_link() is w_first
    assert linkedlist.last_link() is w_first
    linkedlist.add_last_link(w_last)
    assert linkedlist.first_link() is w_first
    assert linkedlist.last_link() is w_last

def new_process(w_next=objtable.w_nil,
                w_my_list=objtable.w_nil,
                w_suspended_context=objtable.w_nil,
                priority=0):
    w_priority = utility.wrap_int(priority)
    w_process = model.W_PointersObject(None, 4)
    process = wrapper.ProcessWrapper(w_process)
    process.store_next_link(w_next)
    process.store_my_list(w_my_list)
    process.store_suspended_context(w_suspended_context)
    process.write(2, w_priority)
    return process

def new_processlist(processes_w=[]):
    w_processlist = model.W_PointersObject(None, 2)
    w_first = objtable.w_nil
    w_last = objtable.w_nil
    for w_process in processes_w[::-1]:
        w_first = newprocess(w_first, w_processlist).w_self
        if w_last is objtable.w_nil:
            w_last = w_first
    pl = wrapper.ProcessListWrapper(w_processlist)
    pl.store_first_link(w_first)
    pl.store_last_link(w_last)
    return pl

def new_prioritylist(prioritydict=None):
    if prioritydict is not None:
        maxpriority = max(prioritydict.keys())
    else:
        maxpriority = 5
        prioritydict = {}
    w_prioritylist = model.W_PointersObject(None, maxpriority)
    prioritylist = wrapper.Wrapper(w_prioritylist)
    for i in range(maxpriority):
        prioritylist.write(i, new_processlist(prioritydict.get(i, [])).w_self)
    
    return prioritylist

def new_scheduler(w_process=objtable.w_nil, prioritydict=None):
    priority_list = new_prioritylist(prioritydict)
    w_scheduler = model.W_PointersObject(None, 2)
    scheduler = wrapper.SchedulerWrapper(w_scheduler)
    scheduler.store_active_process(w_process)
    scheduler.write(0, priority_list.w_self)
    return scheduler



class TestScheduler(object):
    def setup_method(self, meth):
        self.old_scheduler = wrapper.scheduler
        wrapper.scheduler = lambda: scheduler
        scheduler = new_scheduler()

    def teardown_method(self, meth):
        wrapper.scheduler = self.old_scheduler

    def test_suspend(self):
        process = new_process(priority=2)
        process.put_to_sleep()
        process_list = wrapper.scheduler().get_process_list(2)
        assert process_list.first_link() is process_list.last_link()
        assert process_list.first_link() is process.w_self

    def old_new_process_consistency(self, process, old_process, interp,
                                    old_active_context, new_active_context):
        scheduler = wrapper.scheduler()
        assert old_process.suspended_context() is old_active_context
        priority_list = scheduler.get_process_list(old_process.priority())
        assert priority_list.first_link() is old_process.w_self
        assert interp.w_active_context() is new_active_context
        assert scheduler.active_process() is process.w_self
        priority_list = wrapper.scheduler().get_process_list(process.priority())
        assert priority_list.first_link() is priority_list.last_link()
        # activate does not remove the process from the process_list.
        # The caller of activate is responsible
        assert priority_list.first_link() is process.w_self

    def test_activate(self):
        interp = interpreter.Interpreter()
        scheduler = wrapper.scheduler()
        process = new_process(priority=2, w_suspended_context=objtable.w_false)
        process.put_to_sleep()
        old_process = new_process(priority=3)
        scheduler.store_active_process(old_process.w_self)
        interp.store_w_active_context(objtable.w_true)
        process.activate(interp)

        self.old_new_process_consistency(process, old_process, interp,
                                         objtable.w_true, objtable.w_false)
       
    def test_resume(self):
        interp = interpreter.Interpreter()
        scheduler = wrapper.scheduler()
        process = new_process(priority=4, w_suspended_context=objtable.w_false)
        process.put_to_sleep()
        old_process = new_process(priority=2)
        scheduler.store_active_process(old_process.w_self)
        interp.store_w_active_context(objtable.w_true)

        process.resume(interp)
        self.old_new_process_consistency(process, old_process, interp,
                                         objtable.w_true, objtable.w_false)

        # Does not reactivate old_process because lower priority
        old_process.resume(interp)
        self.old_new_process_consistency(process, old_process, interp,
                                         objtable.w_true, objtable.w_false)


