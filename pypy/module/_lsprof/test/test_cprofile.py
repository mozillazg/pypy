
import py
from pypy.conftest import gettestobjspace

class AppTestCProfile(object):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_lsprof',))
        cls.w_expected_output = space.wrap(expected_output)
        cls.space = space
        cls.w_file = space.wrap(__file__)
    
    def test_cprofile(self):
        import sys, os
        # XXX this is evil trickery to walk around the fact that we don't
        #     have __file__ at app-level here
        sys.path.insert(0, os.path.dirname(self.file))
        try:
            from cProfile import Profile
            from profilee import testfunc, timer

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
                return results, prof

            res, prof = do_profiling(Profile)
            assert res[0] == 1000
            for i, method in enumerate(methodnames):
                if not res[i + 1] == self.expected_output[method]:
                    print method
                    print res[i + 1]
                    print self.expected_output[method]
                    one = res[i + 1].split("\n")
                    two = self.expected_output[method].split("\n")
                    for k in range(len(res[i + 1])):
                        if one[k] != two[k]:
                            print k
                            print one[k]
                            print two[k]
                            import pdb
                            pdb.set_trace()
                    assert 0
                #assert res[i + 1] == self.expected_output[method]
        finally:
            sys.path.pop(0)

expected_output = {}
expected_output['print_stats'] = """\
         98 function calls (78 primitive calls) in 1.000 CPU seconds

   Ordered by: standard name

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    1.000    1.000 <string>:0(<module>)
        1    0.000    0.000    0.000    0.000 ?:1(<module>)
       28    0.028    0.001    0.028    0.001 profilee.py:110(__getattr__)
        1    0.270    0.270    1.000    1.000 profilee.py:25(testfunc)
     23/3    0.150    0.007    0.170    0.057 profilee.py:35(factorial)
       20    0.020    0.001    0.020    0.001 profilee.py:48(mul)
        2    0.040    0.020    0.600    0.300 profilee.py:55(helper)
        4    0.116    0.029    0.120    0.030 profilee.py:73(helper1)
        2    0.000    0.000    0.140    0.070 profilee.py:84(helper2_indirect)
        8    0.312    0.039    0.400    0.050 profilee.py:88(helper2)
        8    0.064    0.008    0.080    0.010 profilee.py:98(subhelper)


"""
expected_output['print_callers'] = """\
   Ordered by: standard name

Function                          was called by...
                                      ncalls  tottime  cumtime
<string>:0(<module>)              <-
?:1(<module>)                     <-
profilee.py:110(__getattr__)      <-       4    0.004    0.004  profilee.py:73(helper1)
                                           8    0.008    0.008  profilee.py:88(helper2)
                                          16    0.016    0.016  profilee.py:98(subhelper)
profilee.py:25(testfunc)          <-       1    0.270    1.000  <string>:0(<module>)
profilee.py:35(factorial)         <-       1    0.014    0.130  profilee.py:25(testfunc)
                                        20/3    0.130    0.147  profilee.py:35(factorial)
                                           2    0.006    0.040  profilee.py:84(helper2_indirect)
profilee.py:48(mul)               <-      20    0.020    0.020  profilee.py:35(factorial)
profilee.py:55(helper)            <-       2    0.040    0.600  profilee.py:25(testfunc)
profilee.py:73(helper1)           <-       4    0.116    0.120  profilee.py:55(helper)
profilee.py:84(helper2_indirect)  <-       2    0.000    0.140  profilee.py:55(helper)
profilee.py:88(helper2)           <-       6    0.234    0.300  profilee.py:55(helper)
                                           2    0.078    0.100  profilee.py:84(helper2_indirect)
profilee.py:98(subhelper)         <-       8    0.064    0.080  profilee.py:88(helper2)


"""
expected_output['print_callees'] = """\
   Ordered by: standard name

Function                          called...
                                      ncalls  tottime  cumtime
<string>:0(<module>)              ->       1    0.270    1.000  profilee.py:25(testfunc)
?:1(<module>)                     ->
profilee.py:110(__getattr__)      ->
profilee.py:25(testfunc)          ->       1    0.014    0.130  profilee.py:35(factorial)
                                           2    0.040    0.600  profilee.py:55(helper)
profilee.py:35(factorial)         ->    20/3    0.130    0.147  profilee.py:35(factorial)
                                          20    0.020    0.020  profilee.py:48(mul)
profilee.py:48(mul)               ->
profilee.py:55(helper)            ->       4    0.116    0.120  profilee.py:73(helper1)
                                           2    0.000    0.140  profilee.py:84(helper2_indirect)
                                           6    0.234    0.300  profilee.py:88(helper2)
profilee.py:73(helper1)           ->       4    0.004    0.004  profilee.py:110(__getattr__)
profilee.py:84(helper2_indirect)  ->       2    0.006    0.040  profilee.py:35(factorial)
                                           2    0.078    0.100  profilee.py:88(helper2)
profilee.py:88(helper2)           ->       8    0.064    0.080  profilee.py:98(subhelper)
                                           8    0.008    0.008  profilee.py:110(__getattr__)
profilee.py:98(subhelper)         ->      16    0.016    0.016  profilee.py:110(__getattr__)


"""

# this is how stuff would look like if we trace built-in calls

real_expected_output = {}
real_expected_output['print_stats'] = """\
         126 function calls (106 primitive calls) in 1.000 CPU seconds

   Ordered by: standard name

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    1.000    1.000 <string>:1(<module>)
       28    0.028    0.001    0.028    0.001 profilee.py:110(__getattr__)
        1    0.270    0.270    1.000    1.000 profilee.py:25(testfunc)
     23/3    0.150    0.007    0.170    0.057 profilee.py:35(factorial)
       20    0.020    0.001    0.020    0.001 profilee.py:48(mul)
        2    0.040    0.020    0.600    0.300 profilee.py:55(helper)
        4    0.116    0.029    0.120    0.030 profilee.py:73(helper1)
        2    0.000    0.000    0.140    0.070 profilee.py:84(helper2_indirect)
        8    0.312    0.039    0.400    0.050 profilee.py:88(helper2)
        8    0.064    0.008    0.080    0.010 profilee.py:98(subhelper)
       12    0.000    0.000    0.012    0.001 {hasattr}
        4    0.000    0.000    0.000    0.000 {method 'append' of 'list' objects}
        1    0.000    0.000    0.000    0.000 {method 'disable' of '_lsprof.Profiler' objects}
        8    0.000    0.000    0.000    0.000 {range}
        4    0.000    0.000    0.000    0.000 {sys.exc_info}


"""
real_expected_output['print_callers'] = """\
   Ordered by: standard name

Function                                          was called by...
                                                      ncalls  tottime  cumtime
<string>:1(<module>)                              <-
profilee.py:110(__getattr__)                      <-      16    0.016    0.016  profilee.py:98(subhelper)
                                                          12    0.012    0.012  {hasattr}
profilee.py:25(testfunc)                          <-       1    0.270    1.000  <string>:1(<module>)
profilee.py:35(factorial)                         <-       1    0.014    0.130  profilee.py:25(testfunc)
                                                        20/3    0.130    0.147  profilee.py:35(factorial)
                                                           2    0.006    0.040  profilee.py:84(helper2_indirect)
profilee.py:48(mul)                               <-      20    0.020    0.020  profilee.py:35(factorial)
profilee.py:55(helper)                            <-       2    0.040    0.600  profilee.py:25(testfunc)
profilee.py:73(helper1)                           <-       4    0.116    0.120  profilee.py:55(helper)
profilee.py:84(helper2_indirect)                  <-       2    0.000    0.140  profilee.py:55(helper)
profilee.py:88(helper2)                           <-       6    0.234    0.300  profilee.py:55(helper)
                                                           2    0.078    0.100  profilee.py:84(helper2_indirect)
profilee.py:98(subhelper)                         <-       8    0.064    0.080  profilee.py:88(helper2)
{hasattr}                                         <-       4    0.000    0.004  profilee.py:73(helper1)
                                                           8    0.000    0.008  profilee.py:88(helper2)
{method 'append' of 'list' objects}               <-       4    0.000    0.000  profilee.py:73(helper1)
{method 'disable' of '_lsprof.Profiler' objects}  <-
{range}                                           <-       8    0.000    0.000  profilee.py:98(subhelper)
{sys.exc_info}                                    <-       4    0.000    0.000  profilee.py:73(helper1)


"""
real_expected_output['print_callees'] = """\
   Ordered by: standard name

Function                                          called...
                                                      ncalls  tottime  cumtime
<string>:1(<module>)                              ->       1    0.270    1.000  profilee.py:25(testfunc)
profilee.py:110(__getattr__)                      ->
profilee.py:25(testfunc)                          ->       1    0.014    0.130  profilee.py:35(factorial)
                                                           2    0.040    0.600  profilee.py:55(helper)
profilee.py:35(factorial)                         ->    20/3    0.130    0.147  profilee.py:35(factorial)
                                                          20    0.020    0.020  profilee.py:48(mul)
profilee.py:48(mul)                               ->
profilee.py:55(helper)                            ->       4    0.116    0.120  profilee.py:73(helper1)
                                                           2    0.000    0.140  profilee.py:84(helper2_indirect)
                                                           6    0.234    0.300  profilee.py:88(helper2)
profilee.py:73(helper1)                           ->       4    0.000    0.004  {hasattr}
                                                           4    0.000    0.000  {method 'append' of 'list' objects}
                                                           4    0.000    0.000  {sys.exc_info}
profilee.py:84(helper2_indirect)                  ->       2    0.006    0.040  profilee.py:35(factorial)
                                                           2    0.078    0.100  profilee.py:88(helper2)
profilee.py:88(helper2)                           ->       8    0.064    0.080  profilee.py:98(subhelper)
                                                           8    0.000    0.008  {hasattr}
profilee.py:98(subhelper)                         ->      16    0.016    0.016  profilee.py:110(__getattr__)
                                                           8    0.000    0.000  {range}
{hasattr}                                         ->      12    0.012    0.012  profilee.py:110(__getattr__)
{method 'append' of 'list' objects}               ->
{method 'disable' of '_lsprof.Profiler' objects}  ->
{range}                                           ->
{sys.exc_info}                                    ->


"""
