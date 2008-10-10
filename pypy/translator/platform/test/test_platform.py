
from pypy.tool.udir import udir
from pypy.translator.platform import host

def test_simple_enough():
    cfile = udir.join('test_simple_enough.c')
    tmpdir = cfile.write('''
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
