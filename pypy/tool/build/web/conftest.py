import py
from py.__.doc.conftest import Directory as Dir, DoctestText, \
                                            ReSTChecker
Option = py.test.config.Option
option = py.test.config.addoptions("pypybuilder test options",
        Option('', '--webcheck',
               action="store_true", dest="webcheck", default=False,
               help=("run (X)HTML validity tests (using "
                     "http://www.w3c.org/validator)")
        ),
)

