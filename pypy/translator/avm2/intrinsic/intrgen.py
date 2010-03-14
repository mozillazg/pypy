
import autopath
import os
import os.path

intrinsic_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))

from pypy.translator.avm2.query import ClassDesc

def get_type(t, resolved={}):
    if "=" in t:
        return get_type(t.split("=")[0].strip(), resolved)
    if t == "*":
        return ""
    elif t == "void":
        return "None"
    elif t == "int":
        return "int"
    elif t == "uint":
        return "uint"
    elif t == "Boolean":
        return "bool"
    elif t == "Number":
        return "float"
    elif t == "String":
        return "unicode"
    elif t == "Array":
        return "list"
    elif t.startswith("Vector.<"):
        return get_type(t[len("Vector.<"):-1]) + "[]"
    elif t in ("Object", "Dictionary"):
        return "dict"
    return resolved.get(t, t)

def parse_file(file):
    
    FullName  = ""
    ShortName = ""
    BaseType  = ""
    Package   = ""
    Resolved  = {}
    Methods   = []
    Fields    = []
    StaticMethods = []
    StaticFields  = []
    
    for line in file:
        line = line.strip().strip(";")
        
        if line.startswith("package "):
            Package = line[len("package "):].strip("{")
        
        elif line.startswith("import "):
            resolvedname = line[len("import "):]
            ns, name = resolvedname.rsplit(".", 1)
            Resolved[name] = resolvedname
        
        elif line.startswith("public class "):
            line = line[len("public class "):].split()
            ShortName = line[0]
            if Package:
                FullName = "%s.%s" % (Package, ShortName)
            else:
                FullName = ShortName
            
            if "extends" in line:
                name = line[2]
                if os.path.exists(os.path.join(os.path.dirname(file.name), name+'.as')):
                    BaseType = '%s.%s' % (Package, name)
                elif os.path.exists(os.path.join(intrinsic_dir, name+'.as')):
                    BaseType = name
                elif name in Resolved:
                    BaseType = Resolved[name]
                else:
                    BaseType = name
                
        elif line.startswith(("public function ", "public static function ")):
            
            prop = Methods
            line = line[len("public "):]
            
            if "static" in line:
                line = line[len("static function "):]
                prop = StaticMethods
            else:
                line = line[len("function "):]

            linearr = line.split()
            
            name = linearr[0]
            if name == ShortName:
                name = "!CONSTRUCTOR!"
            
            arglist = line[line.find("(")+1:]
            if name == "!CONSTRUCTOR!":
                rettype = None
            else:
                rettype = get_type(arglist[arglist.rfind(":")+2:], Resolved)
                
            args = [arg for arg in arglist[:arglist.find(")")].split(",")]
            args = [(get_type(arg.strip().split(":")[1], Resolved) if ":" in arg else ("*args" if "..." in arg else arg.strip())) for arg in args]

            if name in ("get", "set"):
                
                if prop == StaticMethods:
                    prop = StaticFields
                else:
                    prop = Fields
                    
                pname = linearr[1]
                if name == "set":
                    type = args[0]
                elif name == "get":
                    type = rettype
                    
                if (pname, type) not in prop:
                    prop.append((pname, type))
            else:
                prop.append((name, args, rettype))
            
        elif line.startswith("public static "):
            line = line.split()
            if ":" in line:
                StaticFields.append((line[3], line[5]))
            else:
                StaticFields.append(tuple(line[3].split(":")))
    
    desc = ClassDesc()
    desc.FullName  = FullName
    desc.ShortName = ShortName
    desc.BaseType  = BaseType
    desc.Package   = Package
    desc.Resolved  = Resolved
    desc.Methods   = Methods
    desc.Fields    = Fields
    desc.StaticMethods = StaticMethods
    desc.StaticFields  = StaticFields
    
    return desc

def print_desc(desc):
    print
    print "desc = ClassDesc()"
    print "desc.FullName  = %r" % desc.FullName
    print "desc.ShortName = %r" % desc.ShortName
    print "desc.Package   = %r" % desc.Package
    print "desc.BaseType  = %r" % desc.BaseType
    print_tuples("Methods", desc.Methods)
    print_tuples("StaticMethods", desc.StaticMethods)
    print_tuples("Fields", desc.Fields)
    print_tuples("StaticFields", desc.StaticFields)
    print "types['%s'] = desc" % desc.FullName
    print "del desc"

def print_tuples(varname, L):
    if len(L):
        print "desc.%s = [" % varname
        for t in L:
            print "  %s," % repr(t)
        print "]"
    else:
        print "desc.%s = []" % varname

print "# This file has been autogenerated by intrgen.py -- DO NOT EDIT"
print 
print "from pypy.translator.avm2.query import ClassDesc"
print 
print "types = {}"

for path, dirs, files in os.walk(intrinsic_dir):
    for filename in files:
        print_desc(parse_file(open(os.path.join(path, filename))))
