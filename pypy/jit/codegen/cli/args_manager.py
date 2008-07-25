from pypy.translator.cli.dotnet import CLR
from pypy.translator.cli import dotnet
System = CLR.System
Assembly = System.Reflection.Assembly
OpCodes = System.Reflection.Emit.OpCodes

class ArgsManager:
    
    def __init__(self):
        self.type_counter = {}
        self.clitype = None
        self.fieldtypes = None
        self.slots = None

    def is_open(self):
        return self.clitype is None

    def getCliType(self):
        assert not self.is_open()
        return self.clitype

    def register(self, args_gv):
        assert self.is_open()
        newcounter = {}
        for gv_arg in args_gv:
            clitype = gv_arg.getCliType()
            newcount = newcounter.get(clitype, 0)
            newcounter[clitype] = newcount+1

        for clitype, newcount in newcounter.iteritems():
            oldcount = self.type_counter.get(clitype, 0)
            maxcount = max(oldcount, newcount)
            self.type_counter[clitype] = maxcount

    def close(self):
        assert self.is_open()
        templates = self._get_templates()
        
        self.fieldtypes = fieldtypes = []
        self.slots = slots = {}
        for clitype, count in self.type_counter.iteritems():
            start = len(fieldtypes)
            end = start+count
            fieldtypes += [clitype]*count
            slots[clitype] = self._myrange(start, end)
        numfields = len(fieldtypes)
        
        if numfields <= len(templates):
            template = templates[numfields-1]
            array = dotnet.new_array(System.Type, numfields)
            for i in range(numfields):
                array[i] = fieldtypes[i]
            self.clitype = template.MakeGenericType(array)
        else:
            assert False, 'TODO'

    def copy_to_inputargs(self, meth, args_gv):
        "copy args_gv into the appropriate fields of inputargs"
        assert not self.is_open()
        il = meth.il
        gv_inputargs = meth.gv_inputargs
        fields = self._get_fields(args_gv)
        assert len(args_gv) == len(fields)
        for i in range(len(args_gv)):
            gv_arg = args_gv[i]
            fieldinfo = fields[i]
            gv_inputargs.load(meth)
            gv_arg.load(meth)
            il.Emit(OpCodes.Stfld, fieldinfo)

    def copy_from_inputargs(self, meth, args_gv):
        "copy the appropriate fields of inputargs into args_gv"
        assert not self.is_open()
        il = meth.il
        gv_inputargs = meth.gv_inputargs
        fields = self._get_fields(args_gv)
        assert len(args_gv) == len(fields)
        for i in range(len(args_gv)):
            gv_arg = args_gv[i]
            fieldinfo = fields[i]
            gv_inputargs.load(meth)
            il.Emit(OpCodes.Ldfld, fieldinfo)
            gv_arg.store(meth)

    def _myrange(self, start, end):
        length = (end - start)
        res = [0] * length
        for i in range(start, end):
            res[i] = i
        return res

    def _load_pypylib(self):
        from pypy.translator.cli.query import pypylib, pypylib2
        assembly = None
        for name in [pypylib, pypylib2]:
            assembly = Assembly.LoadWithPartialName(name)
            if assembly:
                break
        assert assembly is not None
        return assembly
    
    def _get_templates(self):
        pypylib = self._load_pypylib()
        templates = []
        i = 1
        while True:
            typename = 'pypy.runtime.InputArgs`%d' % i
            clitype = pypylib.GetType(typename)
            if not clitype:
                break
            templates.append(clitype)
            i += 1
        return templates

    def _copy_slots(self):
        'Deepcopy self.slots'
        slots = {}
        for key, value in self.slots.iteritems():
            slots[key] = value[:]
        return slots

    def _get_fields(self, args_gv):
        slots = self._copy_slots()
        types = [gv_arg.getCliType() for gv_arg in args_gv]
        fields = []
        for clitype in types:
            slot = slots[clitype].pop()
            fieldinfo = self.clitype.GetField('field%d' % slot)
            fields.append(fieldinfo)
        return fields
