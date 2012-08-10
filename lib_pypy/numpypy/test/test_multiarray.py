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
   raises(TypeError, multiarray.count_nonzero, 'a')
