import os
from pypy.translator.cli.dotnet import CLR
from pypy.translator.cli import dotnet
System = CLR.System
Utils = CLR.pypy.runtime.Utils
AutoSaveAssembly = CLR.pypy.runtime.AutoSaveAssembly
MethodAttributes = System.Reflection.MethodAttributes
TypeAttributes = System.Reflection.TypeAttributes

class AbstractMethodBuilder:
    
    def get_il_generator(self):
        raise NotImplementedError

    def create_delegate(self, delegatetype, consts):
        raise NotImplementedError

class DynamicMethodBuilder(AbstractMethodBuilder):
    
    def __init__(self, name, res, args):
        self.dynmeth = Utils.CreateDynamicMethod(name, res, args)

    def get_il_generator(self): 
        return self.dynmeth.GetILGenerator()

    def create_delegate(self, delegatetype, consts):
        return self.dynmeth.CreateDelegate(delegatetype, consts)


# the assemblyData singleton contains the informations about the
# assembly we are currently writing to
class AssemblyData:
    assembly = None
    name = None

    def is_enabled(self):
        if self.name is None:
            name = os.environ.get('PYPYJITLOG')
            if name is None:
                name = ''
            self.name = name
        return bool(self.name)

    def create(self):
        assert self.is_enabled()
        if self.assembly is None:
            name = self.name
            self.auto_save_assembly = AutoSaveAssembly.Create(name)
            self.assembly = self.auto_save_assembly.GetAssemblyBuilder()
            self.module = self.assembly.DefineDynamicModule(name)
        
assemblyData = AssemblyData()


class AssemblyMethodBuilder(AbstractMethodBuilder):
    
    def __init__(self, name, res, args):
        module = assemblyData.module
        self.typeBuilder = AutoSaveAssembly.DefineType(module, name)
        self.meth = AutoSaveAssembly.DefineMethod(self.typeBuilder,
                                                  "invoke", res, args)


    def get_il_generator(self):
        return self.meth.GetILGenerator()

    def create_delegate(self, delegatetype, consts):
        t = self.typeBuilder.CreateType()
        methinfo = t.GetMethod("invoke")
        return System.Delegate.CreateDelegate(delegatetype,
                                              consts,
                                              methinfo)

def get_methodbuilder(name, res, args):
    if assemblyData.is_enabled():
        assemblyData.create()
        return AssemblyMethodBuilder(name, res, args)
    else:
        return DynamicMethodBuilder(name, res, args)

