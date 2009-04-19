from pypy.lib import hashlib, _hashlib

def test_unicode():
    assert isinstance(hashlib.new('sha1', u'xxx'), _hashlib.hash)

def test_attributes():
    for name, expected_size in {'md5': 16,
                                'sha1': 20,
                                'sha224': 28,
                                'sha256': 32,
                                'sha384': 48,
                                'sha512': 64,
                                }.items():
        h = hashlib.new(name)
        assert h.digest_size == expected_size
        assert h.digestsize == expected_size

        # also test the pure Python implementation
        h = hashlib.__get_builtin_constructor(name)('')
        assert h.digest_size == expected_size
        assert h.digestsize == expected_size
