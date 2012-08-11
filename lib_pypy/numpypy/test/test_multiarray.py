try:
    import _numpypy as np
    import numpypy.multiarray as multiarray
    numpypy = True
except:
    import numpy as np
    from numpy.core import multiarray
    numpypy = False

from py.test import raises

def test_count_nonzero():
    a = np.array([[1, 1], [1, 1]])
    assert multiarray.count_nonzero(a) == 4
    assert multiarray.count_nonzero('a') == 1
    assert multiarray.count_nonzero(('a',2)) == 2 

def test_empty_like():
    a = np.array([[1, 1], [1, 1]])
    b = multiarray.empty_like(a)
    b[0,0] = 100
    assert b[0,0] != a[0,0]
    assert b.shape == a.shape
    assert b.dtype == a.dtype
    b = multiarray.empty_like(a, dtype=float)
    assert b.dtype == np.dtype(float)
    if numpypy:
        raises(ValueError, multiarray.empty_like, a, order='F')

def test_fromiter():
    iterable = (x*x for x in range(5))
    b = multiarray.fromiter(iterable, np.dtype(float))
    assert b.dtype == np.dtype(float)
    assert all(b == [0., 1., 4., 9., 16.]) == True
