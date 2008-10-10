
import py
from pypy.tool.udir import udir
from pypy.translator.platform import host, CompilationError

def test_simple_enough():
    cfile = udir.join('test_simple_enough.c')
    cfile.write('''
    #include <stdio.h>
    int main()
    {
        printf("42\\n");
        return 0;
    }
    ''')
    executable = host.compile([cfile], None)
    res = host.execute(executable)
    assert res.out == '42\n'
    assert res.err == ''
    assert res.returncode == 0

def test_nice_errors():
    cfile = udir.join('test_nice_errors.c')
    cfile.write('')
    try:
        executable = host.compile([cfile], None)
    except CompilationError, e:
        filename = cfile.dirpath().join(cfile.purebasename + '.errors')
        assert filename.read() == e.err
    else:
        py.test.fail("Did not raise")
    
