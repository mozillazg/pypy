import py
from pypy.jit.backend import detect_cpu

class Module(py.test.collect.Module):
    def collect(self):
        cpu = detect_cpu.autodetect()
        if cpu not in ('x86', 'x86_64'):
            py.test.skip("c/gcc directory skipped: cpu is %r" % (cpu,))
        return super(Module, self).collect()
