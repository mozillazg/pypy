import autopath


objspacename = 'std'

class TestW_BoolObject:

    def setup_method(self,method):
        self.true = self.space.w_True
        self.false = self.space.w_False
        self.wrap = self.space.wrap

    def test_repr(self):
        assert self.space.eq_w(self.space.repr(self.true), self.wrap("True"))
        assert self.space.eq_w(self.space.repr(self.false), self.wrap("False"))
    
    def test_true(self):
        assert self.space.is_true(self.true)
        
    def test_false(self):
        assert not self.space.is_true(self.false)
        
class AppTestAppBoolTest:
    def test_bool_callable(self):
        assert True == bool(1)
        assert False == bool(0)
        assert False == bool()

    def test_bool_string(self):
        assert "True" == str(True)
        assert "False" == str(False)
        assert "True" == repr(True)
        assert "False" == repr(False)
