
from pypy.interpreter.executioncontext import ExecutionContext, TRACE_CALL,\
     TRACE_RETURN

class MockExecutionContext(ExecutionContext):
    _jitted = False

    def _we_are_jitted(self):
        return self._jitted
    
    def enter_jit(self):
        self._jitted = True

    def leave_jit(self):
        self._jitted = False

    def call(self, frame):
        self.enter(frame)
        self.call_trace(frame)

class MockFrame(object):
    w_f_trace         = None
    last_exception    = None
    
    def hide(self):
        return False

class TestProfiling(object):
    def test_no_jit(self):
        events = []
        def profilefunc(space, ignored, frame, event, w_arg):
            events.append(event)
        
        ec = MockExecutionContext(self.space)
        frame = MockFrame()
        ec.setllprofile(profilefunc, self.space.w_None)
        ec.call(frame)
        ec.leave(frame)
        assert events == [TRACE_CALL, TRACE_RETURN]

    def test_inlined_call(self):
        events = []
        def profilefunc(space, ignored, frame, event, w_arg):
            events.append((event, frame))
        
        ec = MockExecutionContext(self.space)
        frame = MockFrame()
        frame2 = MockFrame()
        ec.setllprofile(profilefunc, self.space.w_None)
        ec.call(frame)
        ec.enter_jit()
        ec.call(frame2)
        ec.leave(frame2)
        ec.call(frame2)
        ec.leave(frame2)
        ec.leave_jit()
        ec.leave(frame)
        assert events == [(TRACE_CALL, frame), (TRACE_RETURN, frame)]

    def test_recursive_call(self):
        events = []
        def profilefunc(space, ignored, frame, event, w_arg):
            events.append((event, frame))
        
        ec = MockExecutionContext(self.space)
                
