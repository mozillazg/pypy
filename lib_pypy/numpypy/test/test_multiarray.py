try:
    import _numpypy as np
    import numpypy.multiarray as multiarray
except:
    import numpy as np
    from numpy.core import multiarray

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
