from rpython.translator.driver import TranslationDriver


def Translation(entry_point, argtypes=None, policy=None, **kwds):
    driver = TranslationDriver(setopts={'translation.verbose': True})
    driver.driver = driver
    driver.config.translation.set(**kwds)
    driver.setup(entry_point, argtypes, policy)
    driver.context = driver.translator
    # for t.view() to work just after construction
    graph = driver.translator.buildflowgraph(entry_point)
    driver.translator._prebuilt_graphs[entry_point] = graph
    return driver
