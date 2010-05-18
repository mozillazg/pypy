import py
from pypy.jit.backend import detect_cpu

cpu = detect_cpu.autodetect()
def pytest_runtest_setup(item):
    # XXX
    if "test_rx86" in str(item.fspath):
        # Don't skip
        pass
    elif cpu != 'x86':
        py.test.skip("x86 tests skipped: cpu is %r" % (cpu,))
