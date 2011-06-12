import sys
from pypy.rlib.rtealet import *
from pypy.rlib.rrandom import Random
from pypy.rlib.nonconst import NonConstant
from pypy.rlib.objectmodel import compute_unique_id
from pypy.rlib.debug import debug_print

def plan_to_do(rand, steps=10000):
    ops = []
    live_tealets = {0: None}
    total = 0
    current = 0
    i = 0
    while i < steps or len(live_tealets) > 1:
        r = rand.random()
        if r < 0.06 and i < steps:
            total += 1
            ops.append(("new", total))
            live_tealets[total] = None
            current = total
        else:
            keys = live_tealets.keys()
            target = keys[int(rand.random() * len(keys))]
            if r < 0.1 and current > 0 and current != target:
                ops.append(("finish", target))
                del live_tealets[current]
            else:
                ops.append(("switch", target))
            current = target
        #print i, len(live_tealets), r
        i += 1
    assert current == 0
    assert live_tealets.keys() == [0]
    ops.append(("done", 0))
    return ops

# ____________________________________________________________

class Replay(object):
    def setup(self, lst, tealets):
        self.lst = lst
        self.index = 0
        self.tealets = tealets
        self.mapping = {}

    def next(self):
        result = self.lst[self.index]
        self.index += 1
        return result

replay = Replay()

class X(object):
    fixed_pattern = 0
    def __init__(self, value):
        if NonConstant(True):
            self.fixed_pattern = 0x6789ABCD
        self.value = value

class MyTealet(Tealet):
    def run(self):
        index = len(replay.tealets)
        self.index = index
        replay.tealets.append(self)
        return_to_index = do(index, X(index))
        replay.tealets[index] = None
        assert 0 <= return_to_index < len(replay.tealets)
        tt = replay.tealets[return_to_index]
        assert tt
        return tt

def do_switch(tt):
    replay.stuff = X(1)
    tt.switch()
do_switch._dont_inline_ = True

def do_new(main):
    MyTealet(main)
do_new._dont_inline_ = True

def do(current_tealet_index, x):
    main = replay.tealets[0]
    assert main
    if compute_unique_id(x) in replay.mapping.values():
        for index1, x1 in replay.mapping.items():
            debug_print("mapping[", index1, "] =", x1)
        debug_print("current_tealet_index =", current_tealet_index)
        debug_print("new object x =", x, "(", compute_unique_id(x), ")")
        assert 0
    replay.mapping[current_tealet_index] = compute_unique_id(x)
    while True:
        #debug_print("in", current_tealet_index, ": x =", x, "(",
        #            compute_unique_id(x), ")")
        assert main.current == replay.tealets[current_tealet_index]
        assert replay.mapping[current_tealet_index] == compute_unique_id(x)
        assert x.fixed_pattern == 0x6789ABCD
        assert x.value == current_tealet_index
        operation, target = replay.next()
        #debug_print("(", operation, target, ")")
        if operation == "switch":
            assert 0 <= target < len(replay.tealets)
            tt = replay.tealets[target]
            assert tt
            do_switch(tt)
        elif operation == "new":
            assert target == len(replay.tealets)
            do_new(main)
        elif operation == "finish":
            assert 0 <= target < len(replay.tealets)
            assert target != current_tealet_index
            del replay.mapping[current_tealet_index]
            return target
        elif operation == "done":
            assert target == current_tealet_index == 0
            return -42
        else:
            assert 0
do._dont_inline_ = True

def run_demo(lst):
    main = MainTealet()
    replay.setup(lst, [main])
    res = do(0, X(0))
    assert res == -42
    for tt in replay.tealets[1:]:
        assert not tt
    assert replay.index == len(replay.lst)

# ____________________________________________________________

def entry_point(argv):
    if len(argv) > 1:
        seed = int(argv[1])
    else:
        seed = 0
    print 'Building plan with seed=%d...' % seed
    lst = plan_to_do(Random(seed))
    print 'Running...'
    run_demo(lst)
    print 'OK'
    return 0

def target(*args):
    return entry_point, None
