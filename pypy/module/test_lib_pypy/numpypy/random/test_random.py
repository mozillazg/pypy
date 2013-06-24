import py
try:
    import numpypy
except:
    pass

def test_mtrand():
    from numpy.random import mtrand
    a = mtrand.random_sample()
    assert isinstance(a, float)
    a = mtrand.random_sample(10)
    assert a.shape == (10,)

def test_randn():
    from numpy.random.mtrand import randn
    from numpy import array
    a = array([randn() for i in xrange(1000)])
    b = randn(1000)
    assert -0.1 < a.mean() < 0.1
    assert -0.1 < b.mean() < 0.1
    assert b.shape == (1000,)
