
from pypy.interpreter.executioncontext import ExecutionContext, TRACE_CALL,\
     TRACE_RETURN

class MockExecutionContext(ExecutionContext):
    pass

class MockFrame(object):
    w_f_trace = None
    last_exception = None
    
    def hide(self):
        return False

class TestProfiling(object):
    def test_simple(self):
        events = []
        def profilefunc(space, ignored, frame, event, w_arg):
            events.append(event)
        
        ec = MockExecutionContext(self.space)
        frame = MockFrame()
        ec.setllprofile(profilefunc, self.space.w_None)
        ec.enter(frame)
        ec.call_trace(frame)
        ec.leave(frame)
        assert events == [TRACE_CALL, TRACE_RETURN]
