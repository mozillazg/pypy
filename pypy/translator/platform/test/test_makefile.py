
from pypy.translator.platform.linux import GnuMakefile as Makefile
from StringIO import StringIO
import re

def test_simple_makefile():
    m = Makefile()
    m.definition('CC', 'xxx')
    m.definition('XX', ['a', 'b', 'c'])
    m.rule('x', 'y', 'do_stuff')
    m.rule('y', 'z', ['a', 'b', 'ced'])
    s = StringIO()
    m.write(s)
    val = s.getvalue()
    expected_lines = [
        r'CC += +xxx',
        r'XX += +a \\\n +b \\\n +c',
        r'^x: y\n\tdo_stuff',
        r'^y: z\n\ta\n\tb\n\tced\n']
    for i in expected_lines:
        assert re.search(i, val, re.M)

