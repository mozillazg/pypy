class Boxes(object):
    pass

def get_real_model():
    class LoopModel(object):
        from pypy.jit.metainterp.history import TreeLoop, JitCellToken
        from pypy.jit.metainterp.resoperation import ConstInt,\
             ConstPtr, ConstFloat
        from pypy.jit.metainterp.history import BasicFailDescr, TargetToken
        from pypy.jit.metainterp.typesystem import llhelper

        from pypy.jit.metainterp.history import get_const_ptr_for_string
        from pypy.jit.metainterp.history import get_const_ptr_for_unicode
        get_const_ptr_for_string = staticmethod(get_const_ptr_for_string)
        get_const_ptr_for_unicode = staticmethod(get_const_ptr_for_unicode)

        @staticmethod
        def convert_to_floatstorage(arg):
            from pypy.jit.codewriter import longlong
            return longlong.getfloatstorage(float(arg))

        @staticmethod
        def ptr_to_int(obj):
            from pypy.jit.codewriter.heaptracker import adr2int
            from pypy.rpython.lltypesystem import llmemory
            return adr2int(llmemory.cast_ptr_to_adr(obj))

        @staticmethod
        def ootype_cast_to_object(obj):
            from pypy.rpython.ootypesystem import ootype
            return ootype.cast_to_object(obj)

    return LoopModel

def get_mock_model():
    class MockLoopModel(object):

        class TreeLoop(object):
            def __init__(self, name):
                self.name = name

        class JitCellToken(object):
            I_am_a_descr = True

        class TargetToken(object):
            def __init__(self, jct):
                pass

        class BasicFailDescr(object):
            I_am_a_descr = True

        class Const(object):
            def __init__(self, value=None):
                self.value = value

            def _get_str(self):
                return str(self.value)

            def is_constant(self):
                return True

        class ConstInt(Const):
            type = 'i'

        class ConstPtr(Const):
            type = 'p'

        class ConstFloat(Const):
            type = 'f'

        @classmethod
        def get_const_ptr_for_string(cls, s):
            return cls.ConstPtr(s)

        @classmethod
        def get_const_ptr_for_unicode(cls, s):
            return cls.ConstPtr(s)

        @staticmethod
        def convert_to_floatstorage(arg):
            return float(arg)

        @staticmethod
        def ptr_to_int(obj):
            return id(obj)

        class llhelper(object):
            pass

    return MockLoopModel


def get_model(use_mock):
    if use_mock:
        model = get_mock_model()
    else:
        model = get_real_model()

    model.ExtendedTreeLoop = model.TreeLoop
    return model
