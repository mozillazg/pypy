

class AppTestReferents(object):

    def test_get_objects(self):
        # XXX this test should be run first, before GcRefs are created.
        import gc
        x = [2, 3, 4]
        lst = gc.get_objects()
        for found in lst:
            if found is x:
                break
        else:
            assert 0, "'x' not found in get_rpy_objects"
        for found in lst:
            if type(found) is gc.GcRef:
                assert 0, "get_objects() returned a GcRef"

    def test_get_rpy_objects(self):
        import gc
        x = [2, 3, 4]
        lst = gc.get_rpy_objects()
        for found in lst:
            if found is x:
                break
        else:
            assert 0, "'x' not found in get_rpy_objects"
        for found in lst:
            if type(found) is gc.GcRef:
                break
        else:
            assert 0, "get_rpy_objects() did not return any GcRef"

    def test_get_rpy_referents(self):
        import gc
        y = 12345
        x = [y]
        lst = gc.get_rpy_referents(x)
        # After translation, 'lst' should contain the RPython-level list
        # (as a GcStruct).  Before translation, the 'wrappeditems' list.
        print lst
        lst2 = [x for x in lst if type(x) is gc.GcRef]
        assert lst2 != []
        # In any case, we should land on 'y' after one or two extra levels
        # of indirection.
        lst3 = []
        for x in lst2: lst3 += gc.get_rpy_referents(x)
        if y not in lst3:
            lst4 = []
            for x in lst3: lst4 += gc.get_rpy_referents(x)
            if y not in lst4:
                assert 0, "does not seem to reach 'y'"

    def test_get_rpy_memory_usage(self):
        import gc
        n = gc.get_rpy_memory_usage(12345)
        print n
        assert 4 <= n <= 64

    def test_get_referents(self):
        import gc
        y = 12345
        z = 23456
        x = [y, z]
        lst = gc.get_referents(x)
        assert y in lst and z in lst

    def test_get_memory_usage(self):
        import gc
        x = [2, 5, 10]
        n = gc.get_rpy_memory_usage(x)
        m = gc.get_memory_usage(x)
        print n, m
        assert 4 <= n < m <= 128
