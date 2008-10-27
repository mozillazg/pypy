from pypy.translator.cli.dotnet import CLR
from pypy.translator.cli.dotnet import typeof
System = CLR.System
OpCodes = System.Reflection.Emit.OpCodes
InputArgs = CLR.pypy.runtime.InputArgs

class BaseArgsManager:

    def getCliType(self):
        return typeof(InputArgs)

    def _group_args_by_type(self, args_gv):
        clitype2gv = {}
        for gv_arg in args_gv:
            clitype = self._normalize_type(gv_arg.getCliType())
            clitype2gv.setdefault(clitype, []).append(gv_arg)
        return clitype2gv
    
    def copy_to_inputargs(self, meth, args_gv):
        clitype2gv = self._group_args_by_type(args_gv)
        for clitype, args_gv in clitype2gv.iteritems():
            # XXX: ensure that we have enough items in the array
            field, elemtype = self._get_array(clitype)
            i = 0
            for gv_arg in args_gv:
                self.stelem(meth, i, gv_arg, field, elemtype)
                i+=1

    def copy_from_inputargs(self, meth, args_gv):
        clitype2gv = self._group_args_by_type(args_gv)
        for clitype, args_gv in clitype2gv.iteritems():
            field, elemtype = self._get_array(clitype)
            i = 0
            for gv_arg in args_gv:
                self.ldelem(meth, i, field, elemtype)
                gv_arg.store(meth)
                i+=1


class ArgsManager(BaseArgsManager):

    def stelem(self, meth, i, gv_arg, field, elemtype):
        meth.gv_inputargs.load(meth)
        meth.il.Emit(OpCodes.Ldfld, field)
        meth.il.Emit(OpCodes.Ldc_I4, i)
        gv_arg.load(meth)
        meth.il.Emit(OpCodes.Stelem, elemtype)

    def ldelem(self, meth, i, field, elemtype):
        meth.gv_inputargs.load(meth)
        meth.il.Emit(OpCodes.Ldfld, field)
        meth.il.Emit(OpCodes.Ldc_I4, i)
        meth.il.Emit(OpCodes.Ldelem, elemtype)

    def _normalize_type(self, clitype):
        # XXX: generalize!
        if clitype == typeof(System.UInt32):
            return typeof(System.Int32)
        return clitype

    def _get_array(self, clitype):
        if clitype == typeof(System.Int32):
            field = typeof(InputArgs).GetField('ints')
        else:
            assert False
        ftype = field.get_FieldType()
        return field, ftype.GetElementType()
