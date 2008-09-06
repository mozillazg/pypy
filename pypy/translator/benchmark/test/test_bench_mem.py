
from pypy.translator.benchmark import bench_mem

def test_basic():
    res = bench_mem.run_child('python', ['-c', 'pass'])
    assert 'python' in res
