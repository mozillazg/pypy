
from pypy.translator.platform import host, CompilationError

def test_echo():
    res = host.execute('echo', '42 24')
    assert res.out == '42 24\n'
    res = host.execute('echo', ['42', '24'])
    assert res.out == '42 24\n'
    
