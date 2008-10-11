import py

from pypy.module.unicodedata import compression

thisfile = py.magic.autopath()
data = thisfile.read()
lines = data.splitlines()
codelist = compression.build_compression_table(lines)

def test_roundtrip():
    for line in lines:
        compressed = compression.compress(codelist, line)
        decompressed = compression.uncompress(codelist, compressed)
        assert decompressed == line

def test_simple():
    names = ['abe', 'abcde', 'abd', 'abab']
    codelist = compression.build_compression_table(names)
    print codelist
    for name in names:
        compressed = compression.compress(codelist, name)
        decompressed = compression.uncompress(codelist, compressed)
        assert decompressed == name

def test_simple2():
    names = ['abc', 'abc', 'abc']
    codelist = compression.build_compression_table(names)
    assert set(codelist) == set(['abc', 'c', 'b', 'a'])
    print codelist
