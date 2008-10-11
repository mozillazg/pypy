
from pypy.translator.platform import host, CompilationError
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.udir import udir
from StringIO import StringIO

def test_echo():
    res = host.execute('echo', '42 24')
    assert res.out == '42 24\n'
    res = host.execute('echo', ['42', '24'])
    assert res.out == '42 24\n'
    
def test_simple_makefile():
    tmpdir = udir.join('simple_makefile').ensure(dir=1)
    cfile = tmpdir.join('test_simple_enough.c')
    cfile.write('''
    #include <stdio.h>
    int main()
    {
        printf("42\\n");
        return 0;
    }
    ''')
    mk = host.gen_makefile([cfile], ExternalCompilationInfo(),
                           path=tmpdir)
    f = tmpdir.join('Makefile').open('w')
    mk.write(f)
    f.close()
    host.execute_makefile(tmpdir)
    res = host.execute(tmpdir.join('test_simple_enough'))
    assert res.out == '42\n'
    assert res.err == ''
    assert res.returncode == 0
    
