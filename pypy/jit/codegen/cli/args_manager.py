from pypy.translator.cli.dotnet import CLR
from pypy.translator.cli import dotnet
System = CLR.System
Assembly = System.Reflection.Assembly
OpCodes = System.Reflection.Emit.OpCodes

def new_type_array(types):
    array = dotnet.new_array(System.Type, len(types))
    for i in range(len(types)):
        array[i] = types[i]
    return array

def MakeGenericType(clitype, paramtypes):
    array = new_type_array(paramtypes)
    return clitype.MakeGenericType(array)

class ArgsManager:
    
    def __init__(self):
        self.type_counter = {}
        self.type_index = {}
        self.clitype = None
        self._init_types()

    def _load_pypylib(self):
        from pypy.translator.cli.query import pypylib, pypylib2
        assembly = None
        for name in [pypylib, pypylib2]:
            assembly = Assembly.LoadWithPartialName(name)
            if assembly:
                break
        assert assembly is not None
        return assembly

    def _init_types(self):
        pypylib = self._load_pypylib()
        self.clitype_InputArgs = pypylib.GetType('pypy.runtime.InputArgs`1')
        self.clitype_Void = pypylib.GetType('pypy.runtime.Void')
        self.clitype_Pair = pypylib.GetType('pypy.runtime.Pair`2')

    def is_open(self):
        return self.clitype is None

    def getCliType(self):
        assert not self.is_open()
        return self.clitype

    def register_types(self, types):
        if not self.is_open():
            return # XXX
        
        assert self.is_open()
        newcounter = {}
        for clitype in types:
            newcount = newcounter.get(clitype, 0)
            newcounter[clitype] = newcount+1

        for clitype, newcount in newcounter.iteritems():
            oldcount = self.type_counter.get(clitype, 0)
            maxcount = max(oldcount, newcount)
            self.type_counter[clitype] = maxcount

    def register(self, args_gv):
        types = [gv_arg.getCliType() for gv_arg in args_gv]
        self.register_types(types)

    def close(self):
        assert self.is_open()
        fieldtypes = []
        for clitype, count in self.type_counter.iteritems():
            self.type_index[clitype] = len(fieldtypes)
            fieldtypes += [clitype] * count

        pairtype = self.clitype_Void
        # iterate over reversed(fieldtypes)
        i = len(fieldtypes)-1
        while True:
            if i < 0:
                break
            fieldtype = fieldtypes[i]
            pairtype = MakeGenericType(self.clitype_Pair, [fieldtype, pairtype])
            i-=1

##         for fieldtype in fieldtypes[::-1]:
##             pairtype = MakeGenericType(self.clitype_Pair, [fieldtype, pairtype])
        self.clitype = MakeGenericType(self.clitype_InputArgs, [pairtype])

    def _store_by_index(self, meth, gv_arg, i):
        head_info = self._load_nth_head(meth, i)
        gv_arg.load(meth)
        meth.il.Emit(OpCodes.Stfld, head_info)

    def _load_by_index(self, meth, i):
        head_info = self._load_nth_head(meth, i)
        meth.il.Emit(OpCodes.Ldfld, head_info)

    def _load_nth_head(self, meth, n):
        il = meth.il
        fields_info = self.clitype.GetField("fields")
        meth.gv_inputargs.load(meth)
        il.Emit(OpCodes.Ldflda, fields_info)

        lastfield_info = fields_info
        for _ in range(n):
            fieldtype = lastfield_info.get_FieldType()
            lastfield_info = fieldtype.GetField("tail")
            il.Emit(OpCodes.Ldflda, lastfield_info)
        fieldtype = lastfield_info.get_FieldType()
        return fieldtype.GetField("head")

    def copy_to_inputargs(self, meth, args_gv):
        "copy args_gv into the appropriate fields of inputargs"
        assert not self.is_open()
        fieldtypes = [gv_arg.getCliType() for gv_arg in args_gv]
        indexes = self._get_indexes(fieldtypes)
        assert len(indexes) == len(fieldtypes)
        for i in range(len(indexes)):
            n = indexes[i]
            gv_arg = args_gv[i]
            self._store_by_index(meth, gv_arg, n)

    def copy_from_inputargs(self, meth, args_gv):
        "copy the appropriate fields of inputargs into args_gv"
        assert not self.is_open()
        fieldtypes = [gv_arg.getCliType() for gv_arg in args_gv]
        indexes = self._get_indexes(fieldtypes)
        assert len(indexes) == len(fieldtypes)
        for i in range(len(indexes)):
            n = indexes[i]
            gv_arg = args_gv[i]
            self._load_by_index(meth, n)
            gv_arg.store(meth)

    def _get_indexes(self, fieldtypes):
        indexes = []
        curtype = None
        curidx = -1
        for fieldtype in fieldtypes:
            if fieldtype != curtype:
                curidx = self.type_index[fieldtype]
                curtype = fieldtype
            else:
                curidx += 1
            indexes.append(curidx)
        return indexes
