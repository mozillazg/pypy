def pytest_addoption(parser):
    group = parser.getgroup("pypy-tamarin options")
    group.addoption('--swf', action="store_const", const="swf", dest="tamtarget", default="swf",
            help="generate a swf and abc and use a browsertest to run")
    group.addoption('--tamarin', action="store_const", const="tamarin", dest="tamtarget",
                    help="generate an abc that uses tamarin")
