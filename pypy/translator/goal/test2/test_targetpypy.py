
from pypy.translator.goal.targetpypystandalone import get_entry_point
from pypy.config.pypyoption import get_pypy_config

class TestTargetPyPy(object):
    def test_run(self):
        config = get_pypy_config(translating=True)
        entry_point = get_entry_point(config)
