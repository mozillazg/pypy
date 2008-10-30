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
            clitype, _ = self._normalize_type(gv_arg.getCliType())
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
                # perform the cast if needed
                if elemtype == typeof(System.Object):
                    meth.il.Emit(OpCodes.Castclass, gv_arg.getCliType())
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
        # we have four kind of types:
        #    - integer types up to 32 bit
        #    - 64 bit integers
        #    - 64 bit floats
        #    - reference types (objects)
        if clitype == typeof(System.Double):
            return clitype, 'floats'
        elif clitype == typeof(System.Int64):
            return clitype, 'longs' # XXX: implement it in pypylib
        elif clitype.get_IsPrimitive():
            return typeof(System.Int32), 'ints'
        else:
            # assume it's a reference type
            return typeof(System.Object), 'objs'

    def _get_array(self, clitype):
        clitype, name = self._normalize_type(clitype)
        field = typeof(InputArgs).GetField(name)
        ftype = field.get_FieldType()
        return field, ftype.GetElementType()
