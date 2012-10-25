import py
from pypy.rlib.objectmodel import r_dict, compute_identity_hash,\
     we_are_translated
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.resoperation import rop
from pypy.rlib.objectmodel import we_are_translated

# ____________________________________________________________
# Misc. utilities

def _findall(Class, name_prefix, op_prefix=None):
    result = []
    for name in dir(Class):
        if name.startswith(name_prefix):
            opname = name[len(name_prefix):]
            if opname.isupper():
                assert hasattr(resoperation.rop, opname)
    for value, name in resoperation.opname.items():
        if op_prefix and not name.startswith(op_prefix):
            continue
        if hasattr(Class, name_prefix + name):
            opclass = resoperation.opclasses[getattr(rop, name)]
            if name[-2] == "_":
                assert name[:-2] in opclass.__name__
            else:
                assert name in opclass.__name__
            result.append((value, opclass, getattr(Class, name_prefix + name)))
    return unrolling_iterable(result)

def make_dispatcher_method(Class, name_prefix, op_prefix=None, default=None):
    ops = _findall(Class, name_prefix, op_prefix)
    def dispatch(self, op, *args):
        if we_are_translated():
            opnum = op.getopnum()
            for value, cls, func in ops:
                if opnum == value:
                    assert isinstance(op, cls)
                    return func(self, op, *args)
            if default:
                return default(self, op, *args)
        else:
            name = resoperation.opname[op.getopnum()]
            func = getattr(Class, name_prefix + name, None)
            if func is not None:
                return func(self, op, *args)
            if default:
                return default(self, op, *args)
    dispatch.func_name = "dispatch_" + name_prefix
    return dispatch


def partition(array, left, right):
    last_item = array[right]
    pivot = last_item.sort_key()
    storeindex = left
    for i in range(left, right):
        if array[i].sort_key() <= pivot:
            array[i], array[storeindex] = array[storeindex], array[i]
            storeindex += 1
    # Move pivot to its final place
    array[storeindex], array[right] = last_item, array[storeindex]
    return storeindex

def quicksort(array, left, right):
    # sort array[left:right+1] (i.e. bounds included)
    if right > left:
        pivotnewindex = partition(array, left, right)
        quicksort(array, left, pivotnewindex - 1)
        quicksort(array, pivotnewindex + 1, right)

def sort_descrs(lst):
    quicksort(lst, 0, len(lst)-1)


def descrlist_hash(l):
    res = 0x345678
    for descr in l:
        y = compute_identity_hash(descr)
        res = intmask((1000003 * res) ^ y)
    return res

def descrlist_eq(l1, l2):
    if len(l1) != len(l2):
        return False
    for i in range(len(l1)):
        if l1[i] is not l2[i]:
            return False
    return True

def descrlist_dict():
    return r_dict(descrlist_eq, descrlist_hash)

# ____________________________________________________________

BUCKET_SIZE = 8192

def new_args_set(has_value=False):
    class ArgsSet(object):
        """ An imprecise dict. If you look it up and it's there, it's correct,
        however we don't care about collisions, so a colliding element can
        kick someone else out
        """
        def __init__(self, bucket_size=BUCKET_SIZE):
            self.buckets = [None] * bucket_size
            if has_value:
                self.values = [None] * bucket_size
            self.bucket_size = bucket_size - 1

        def get(self, op):
            hash = op._get_hash_() & self.bucket_size
            candidate = self.buckets[hash]
            if candidate is None:
                return None
            if candidate.__class__ != op.__class__:
                return None # collision
            if op.eq(candidate):
                if has_value:
                    return self.values[hash]
                return candidate
            return None

        if has_value:
            def set(self, op, v):
                hash = op._get_hash_() & self.bucket_size
                if self.buckets[hash] is not None and not self.buckets[hash].eq(op):
                    import pdb
                    pdb.set_trace()
                self.buckets[hash] = op # don't care about collisions
                self.values[hash] = v
        else:
            def add(self, op):
                hash = op._get_hash_() & self.bucket_size
                self.buckets[hash] = op # don't care about collisions

        def copy(self):
            a = ArgsSet()
            a.buckets = self.buckets[:]
            if has_value:
                a.values = self.values[:]
            return a

        if has_value:
            def __repr__(self):
                return 'ArgsDict(%s)' % (['%s: %s' % (item, self.values[i])
                                          for i, item in
                                          enumerate(self.buckets)
                                          if item is not None],)
        else:
            def __repr__(self):
                return 'ArgsSet(%s)' % ([item for item in self.buckets
                                         if item is not None],)

        def __len__(self):
            return len([item for item in self.buckets if item is not None])
    return ArgsSet
ArgsSet = new_args_set()
ArgsDict = new_args_set(True)

# ____________________________________________________________

def equaloplists(oplist1, oplist2, strict_fail_args=True, remap={},
                 text_right=None):
    # try to use the full width of the terminal to display the list
    # unfortunately, does not work with the default capture method of py.test
    # (which is fd), you you need to use either -s or --capture=sys, else you
    # get the standard 80 columns width
    totwidth = py.io.get_terminal_width()
    width = totwidth / 2 - 1
    print ' Comparing lists '.center(totwidth, '-')
    text_right = text_right or 'expected'
    print '%s| %s' % ('optimized'.center(width), text_right.center(width))
    for op1, op2 in zip(oplist1, oplist2):
        txt1 = repr(op1)
        txt2 = repr(op2)
        while txt1 or txt2:
            print '%s| %s' % (txt1[:width].ljust(width), txt2[:width])
            txt1 = txt1[width:]
            txt2 = txt2[width:]
        assert op1.getopnum() == op2.getopnum()
        assert op1.numargs() == op2.numargs()
        for i in range(op1.numargs()):
            x = op1.getarg(i)
            y = op2.getarg(i)
            assert x.eq(remap.get(y, y))
        if op2 in remap:
            if op2 is None:
                assert op1 == remap[op2]
            else:
                assert op1.eq(remap[op2])
        else:
            remap[op2] = op1
        if op1.is_guard():
            assert op2.is_guard()
            # if op1.get_extra("failargs") or op2.get_extra("failargs"):
            #     assert (len(op1.get_extra("failargs")) ==
            #             len(op2.get_extra("failargs")))
            #     if strict_fail_args:
            #         for x, y in zip(op1.get_extra("failargs"),
            #                         op2.get_extra("failargs")):
            #             if x is None:
            #                 assert remap.get(y, y) is None
            #             else:
            #                 assert x.eq(remap.get(y, y))
            #     else:
            #         fail_args1 = set(op1.get_extra("failargs"))
            #         fail_args2 = set([remap.get(y, y) for y in
            #                           op2.get_extra("failargs")])
            #         for x in fail_args1:
            #             for y in fail_args2:
            #                 if x.eq(y):
            #                     fail_args2.remove(y)
            #                     break
            #             else:
            #                 assert False
        elif op1.getopnum() not in (rop.JUMP, rop.LABEL):      # xxx obscure
            assert op1.getdescr() == op2.getdescr()
    assert len(oplist1) == len(oplist2)
    print '-'*totwidth
    return True

