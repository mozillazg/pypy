from pypy.lang.io.model import W_Object
from pypy.rlib.rcoroutine import make_coroutine_classes
d = make_coroutine_classes(W_Object)

Coroutine = d['Coroutine']
AbstractThunk = d['AbstractThunk']
BaseCoState = d['BaseCoState']


class W_Coroutine(Coroutine):
    def __init__(self, space, state, protos):
        Coroutine.__init__(self, state)
        
        W_Object.__init__(self, space, protos)

    def clone(self):
        return W_Coroutine(self.space, self.state, [self])
    
    @staticmethod
    def w_getcurrent(space):
        return W_Coroutine._get_state(space).current

    @staticmethod
    def _get_state(space):
        # XXX: Need a propper caching machinery
        if not hasattr(space, '_coroutine_state'):
            space._coroutine_state = AppCoState(space)
            space._coroutine_state.post_install()
        return space._coroutine_state

class AppCoState(BaseCoState):
    def __init__(self, space):
        BaseCoState.__init__(self)
        self.w_tempval = space.w_nil
        self.space = space
        
    def post_install(self):
        self.current = self.main = W_Coroutine(self.space, self, [self.space.w_object])
        # self.main.subctx.framestack = None    # wack

class IoThunk(AbstractThunk):
    def __init__(self, space, w_message, w_receiver, w_context):
        self.space = space
        self.w_message = w_message
        self.w_receiver = w_receiver
        self.w_context = w_context
    
    def call(self):
        self.w_message.eval(self.space, self.w_receiver, self.w_context)