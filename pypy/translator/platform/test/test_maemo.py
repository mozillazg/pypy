
""" File containing maemo platform tests
"""

from pypy.translator.platform.maemo import Maemo, check_scratchbox
from pypy.translator.platform.test.test_platform import TestPlatform as BasicTest

class TestMaemo(BasicTest):
    platform = Maemo()
    strict_on_stderr = False

    def setup_class(cls):
        check_scratchbox()
