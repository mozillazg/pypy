import autopath

from pypy.tool import test

class TestBuiltinApp(test.AppTestCase):
    def setUp(self):
        self.space = test.objspace()
    
    def test_import(self):
        import types
        d = {}
        m = __import__('quopri', d, d, [])
        self.assertEquals(type(m), types.ModuleType)

    def test_chr(self):
        self.assertEquals(chr(65), 'A')
        self.assertRaises(ValueError, chr, -1)
        self.assertRaises(TypeError, chr, 'a')

    def test_type_selftest(self):
        self.assert_(type(type) is type)

    def test_xrange_args(self):
        x = xrange(2)
        self.assertEquals(x.start, 0)
        self.assertEquals(x.stop, 2)
        self.assertEquals(x.step, 1)

        x = xrange(2,10,2)
        self.assertEquals(x.start, 2)
        self.assertEquals(x.stop, 10)
        self.assertEquals(x.step, 2)

        self.assertRaises(ValueError, xrange, 0, 1, 0) 

    def test_xrange_up(self):
        x = xrange(2)
        self.assertEquals(x.start, 0)
        self.assertEquals(x.stop, 2)
        self.assertEquals(x.step, 1)

        iter_x = iter(x)
        self.assertEquals(iter_x.next(), 0)
        self.assertEquals(iter_x.next(), 1)
        self.assertRaises(StopIteration, iter_x.next)

    def test_xrange_down(self):
        x = xrange(4,2,-1)

        iter_x = iter(x)
        self.assertEquals(iter_x.next(), 4)
        self.assertEquals(iter_x.next(), 3)
        self.assertRaises(StopIteration, iter_x.next)

class TestCmp(test.TestCase):
   
    def test_cmp(self):
       self.failUnless(cmp(9, 9) == 0)
       self.failUnless(cmp(0,9) < 0)
       self.failUnless(cmp(9,0) > 0)
 
if __name__ == '__main__':
    test.main()
 
