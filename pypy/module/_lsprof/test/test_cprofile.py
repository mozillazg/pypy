
from pypy.conftest import gettestobjspace

class AppTestCProfile(object):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_lsprof',))
        cls.w_expected_output = space.wrap(expected_output)
        cls.space = space
    
    def test_cprofile(self):
        skip("fails")
        import sys
        from cProfile import Profile
        from test.profilee import testfunc, timer
        
        methodnames = ['print_stats', 'print_callers', 'print_callees']

        def do_profiling(cls):
            results = []
            prof = cls(timer, 0.001)
            start_timer = timer()
            prof.runctx("testfunc()", {'testfunc':testfunc}, locals())
            results.append(timer() - start_timer)
            for methodname in methodnames:
                import pstats
                from StringIO import StringIO
                s = StringIO()
                stats = pstats.Stats(prof, stream=s)
                stats.strip_dirs().sort_stats("stdname")
                getattr(stats, methodname)()
                results.append(s.getvalue())
            return results

        res = do_profiling(Profile)
        assert res[0] == 1000
        for i, method in enumerate(methodnames):
            if not res[i + 1] == self.expected_output[method]:
                print method
                print res[i + 1]
                print self.expected_output[method]
                assert 0
            #assert res[i + 1] == self.expected_output[method]

expected_output = {}
expected_output['print_stats'] = """\
         127 function calls (107 primitive calls) in 999.749 CPU seconds

   Ordered by: standard name

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        4   -0.004   -0.001   -0.004   -0.001 :0(append)
        4   -0.004   -0.001   -0.004   -0.001 :0(exc_info)
       12   -0.024   -0.002   11.964    0.997 :0(hasattr)
        8   -0.008   -0.001   -0.008   -0.001 :0(range)
        1    0.000    0.000    0.000    0.000 :0(setprofile)
        1   -0.002   -0.002  999.751  999.751 <string>:1(<module>)
        0    0.000             0.000          profile:0(profiler)
        1   -0.002   -0.002  999.749  999.749 profile:0(testfunc())
       28   27.972    0.999   27.972    0.999 profilee.py:110(__getattr__)
        1  269.996  269.996  999.753  999.753 profilee.py:25(testfunc)
     23/3  149.937    6.519  169.917   56.639 profilee.py:35(factorial)
       20   19.980    0.999   19.980    0.999 profilee.py:48(mul)
        2   39.986   19.993  599.814  299.907 profilee.py:55(helper)
        4  115.984   28.996  119.964   29.991 profilee.py:73(helper1)
        2   -0.006   -0.003  139.942   69.971 profilee.py:84(helper2_indirect)
        8  311.976   38.997  399.896   49.987 profilee.py:88(helper2)
        8   63.968    7.996   79.944    9.993 profilee.py:98(subhelper)


"""
expected_output['print_callers'] = """\
   Ordered by: standard name

Function                          was called by...
:0(append)                        <- profilee.py:73(helper1)(4)  119.964
:0(exc_info)                      <- profilee.py:73(helper1)(4)  119.964
:0(hasattr)                       <- profilee.py:73(helper1)(4)  119.964
                                     profilee.py:88(helper2)(8)  399.896
:0(range)                         <- profilee.py:98(subhelper)(8)   79.944
:0(setprofile)                    <- profile:0(testfunc())(1)  999.749
<string>:1(<module>)              <- profile:0(testfunc())(1)  999.749
profile:0(profiler)               <-
profile:0(testfunc())             <- profile:0(profiler)(1)    0.000
profilee.py:110(__getattr__)      <- :0(hasattr)(12)   11.964
                                     profilee.py:98(subhelper)(16)   79.944
profilee.py:25(testfunc)          <- <string>:1(<module>)(1)  999.751
profilee.py:35(factorial)         <- profilee.py:25(testfunc)(1)  999.753
                                     profilee.py:35(factorial)(20)  169.917
                                     profilee.py:84(helper2_indirect)(2)  139.942
profilee.py:48(mul)               <- profilee.py:35(factorial)(20)  169.917
profilee.py:55(helper)            <- profilee.py:25(testfunc)(2)  999.753
profilee.py:73(helper1)           <- profilee.py:55(helper)(4)  599.814
profilee.py:84(helper2_indirect)  <- profilee.py:55(helper)(2)  599.814
profilee.py:88(helper2)           <- profilee.py:55(helper)(6)  599.814
                                     profilee.py:84(helper2_indirect)(2)  139.942
profilee.py:98(subhelper)         <- profilee.py:88(helper2)(8)  399.896


"""
expected_output['print_callees'] = """\
   Ordered by: standard name

Function                          called...
:0(append)                        ->
:0(exc_info)                      ->
:0(hasattr)                       -> profilee.py:110(__getattr__)(12)   27.972
:0(range)                         ->
:0(setprofile)                    ->
<string>:1(<module>)              -> profilee.py:25(testfunc)(1)  999.753
profile:0(profiler)               -> profile:0(testfunc())(1)  999.749
profile:0(testfunc())             -> :0(setprofile)(1)    0.000
                                     <string>:1(<module>)(1)  999.751
profilee.py:110(__getattr__)      ->
profilee.py:25(testfunc)          -> profilee.py:35(factorial)(1)  169.917
                                     profilee.py:55(helper)(2)  599.814
profilee.py:35(factorial)         -> profilee.py:35(factorial)(20)  169.917
                                     profilee.py:48(mul)(20)   19.980
profilee.py:48(mul)               ->
profilee.py:55(helper)            -> profilee.py:73(helper1)(4)  119.964
                                     profilee.py:84(helper2_indirect)(2)  139.942
                                     profilee.py:88(helper2)(6)  399.896
profilee.py:73(helper1)           -> :0(append)(4)   -0.004
                                     :0(exc_info)(4)   -0.004
                                     :0(hasattr)(4)   11.964
profilee.py:84(helper2_indirect)  -> profilee.py:35(factorial)(2)  169.917
                                     profilee.py:88(helper2)(2)  399.896
profilee.py:88(helper2)           -> :0(hasattr)(8)   11.964
                                     profilee.py:98(subhelper)(8)   79.944
profilee.py:98(subhelper)         -> :0(range)(8)   -0.008
                                     profilee.py:110(__getattr__)(16)   27.972


"""
