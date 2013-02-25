from rpython.translator.translator import TranslationContext
from rpython.translator import driver


DEFAULTS = {
  'translation.verbose': True,
}

class Translation(object):

    def __init__(self, entry_point, argtypes=None, **kwds):
        self.driver = driver.TranslationDriver(overrides=DEFAULTS)
        self.config = self.driver.config

        self.entry_point = entry_point
        self.context = TranslationContext(config=self.config)

        policy = kwds.pop('policy', None)
        self.update_options(kwds)
        self.ensure_setup(argtypes, policy)
        # for t.view() to work just after construction
        graph = self.context.buildflowgraph(entry_point)
        self.context._prebuilt_graphs[entry_point] = graph

    def view(self):
        self.context.view()

    def viewcg(self):
        self.context.viewcg()

    def ensure_setup(self, argtypes=None, policy=None):
        standalone = argtypes is None
        if standalone:
            assert argtypes is None
        else:
            if argtypes is None:
                argtypes = []
        self.driver.setup(self.entry_point, argtypes, policy,
                          empty_translator=self.context)
        self.ann_argtypes = argtypes
        self.ann_policy = policy

    def update_options(self, kwds):
        gc = kwds.pop('gc', None)
        if gc:
            self.config.translation.gc = gc
        self.config.translation.set(**kwds)

    def set_backend_extra_options(self, **extra_options):
        for name in extra_options:
            backend, option = name.split('_', 1)
            assert self.config.translation.backend == backend
        self.driver.set_backend_extra_options(extra_options)

    # backend independent

    def annotate(self, **kwds):
        return self.driver.annotate()

    # type system dependent

    def rtype(self):
        return self.driver.rtype()

    def backendopt(self):
        return self.driver.backendopt()

    # backend depedent

    def source(self):
        return self.driver.source()

    def compile(self):
        self.driver.compile()
        return self.driver.c_entryp
