
from pypy.translator.benchmark import bench_mem
import time

def test_compute_memory_usage():
    pid = bench_mem.run_child('python', ['-c', 'import time;time.sleep(1)'])
    time.sleep(.3)
    assert pid
    res = open('/proc/%d/smaps' % pid).read()
    parsed = bench_mem.parse_smaps_output(res)
    assert parsed.shared
    assert parsed.private

def test_parse():
    res = bench_mem.parse_smaps_output(example_data)
    assert res.private == 796 + 120 + 924
    assert res.shared == 60
    assert res.priv_map == {
        '/usr/bin/python2.5': 796 + 120,
        '[heap]'            : 924,
        }
    assert res.shared_map == {
        '/lib/libncurses.so.5.6' : 60,
       }

def test_run_cooperative():
    def f(read, write):
        x = read()
        assert x == 'y'
        write('x')
    
    read, write, pid = bench_mem.run_cooperative(f)
    assert pid
    write('y')
    assert read() == 'x'

def test_measure_cooperative():
    def f1(read, write):
        write('g')
        read()
        write('g')
        read()
        write('e')

    def measure(arg):
        return 42

    measurments = bench_mem.measure(measure, [f1, f1])
    assert measurments == [[42, 42], [42, 42]]

example_data = '''
08048000-0813f000 r-xp 00000000 fd:00 75457      /usr/bin/python2.5
Size:                988 kB
Rss:                 796 kB
Shared_Clean:          0 kB
Shared_Dirty:          0 kB
Private_Clean:       796 kB
Private_Dirty:         0 kB
Referenced:          796 kB
0813f000-08164000 rw-p 000f6000 fd:00 75457      /usr/bin/python2.5
Size:                148 kB
Rss:                 120 kB
Shared_Clean:          0 kB
Shared_Dirty:          0 kB
Private_Clean:        12 kB
Private_Dirty:       108 kB
Referenced:          120 kB
08164000-0825c000 rw-p 08164000 00:00 0          [heap]
Size:                992 kB
Rss:                 924 kB
Shared_Clean:          0 kB
Shared_Dirty:          0 kB
Private_Clean:         0 kB
Private_Dirty:       924 kB
Referenced:          924 kB
b7baf000-b7beb000 r-xp 00000000 08:01 218        /lib/libncurses.so.5.6
Size:                240 kB
Rss:                  60 kB
Shared_Clean:         60 kB
Shared_Dirty:          0 kB
Private_Clean:         0 kB
Private_Dirty:         0 kB
Referenced:           60 kB
'''
