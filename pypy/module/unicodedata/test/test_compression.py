import py

from pypy.module.unicodedata import compression

thisfile = py.magic.autopath()
data = thisfile.read()
lines = data.splitlines()
codetable, codelist = compression.build_compression_table(lines)

def test_tables_sanity():
    for key, value in codetable.items():
        assert codelist[value] == key

def test_roundtrip():
    for line in lines:
        compressed = compression.compress(codetable, line)
        decompressed = compression.uncompress(codelist, compressed)
        assert decompressed == line
