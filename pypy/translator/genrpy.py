"""
Implementation of a translator from application Python to interpreter level RPython.

The idea is that we can automatically transform app-space implementations
of methods into some equivalent representation at interpreter level.
Then, the RPython to C translation might hopefully spit out some
more efficient code than always interpreting these methods.

Note that the appspace functions are treated as rpythonic, in a sense
that globals are constants, for instance. This definition is not
exact and might change.

This module is very much under construction and not yet usable for much
more than testing.
"""
from __future__ import generators
import autopath, os, sys, exceptions
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.objspace.flow.model import traverse, uniqueitems, checkgraph
from pypy.translator.simplify import remove_direct_loops
from pypy.interpreter.pycode import CO_VARARGS
from pypy.annotation import model as annmodel
from types import FunctionType, CodeType

from pypy.objspace.std.restricted_int import r_int, r_uint

from pypy.translator.translator import Translator
from pypy.objspace.std import StdObjSpace

from pypy.interpreter.gateway import app2interp, interp2app


# ____________________________________________________________

def c_string(s):
    return '"%s"' % (s.replace('\\', '\\\\').replace('"', '\"'),)

def uniquemodulename(name, SEEN={}):
    # never reuse the same module name within a Python session!
    i = 0
    while True:
        i += 1
        result = '%s_%d' % (name, i)
        if result not in SEEN:
            SEEN[result] = True
            return result

def go_figure_out_this_name(source):
    # ahem
    return 'PyRun_String("%s", Py_eval_input, PyEval_GetGlobals(), NULL)' % (
        source, )



def ordered_blocks(graph):
    # collect all blocks
    allblocks = []
    def visit(block):
        if isinstance(block, Block):
            # first we order by offset in the code string
            if block.operations:
                ofs = block.operations[0].offset
            else:
                ofs = sys.maxint
            # then we order by input variable name or value
            if block.inputargs:
                txt = str(block.inputargs[0])
            else:
                txt = "dummy"
            allblocks.append((ofs, txt, block))
    traverse(visit, graph)
    allblocks.sort()
    #for ofs, txt, block in allblocks:
    #    print ofs, txt, block
    return [block for ofs, txt, block in allblocks]


class GenRpy:
    def __init__(self, f, translator, modname=None, f2=None, f2name=None):
        self.f = f
        self.f2 = f2
        self.f2name = f2name
        self.translator = translator
        self.modname = (modname or
                        uniquemodulename(translator.functions[0].__name__))
        self.rpynames = {Constant(None).key:  'space.w_None',
                         Constant(False).key: 'space.w_False',
                         Constant(True).key:  'space.w_True',
                       }
        
        self.seennames = {}
        self.initcode = []     # list of lines for the module's initxxx()
        self.latercode = []    # list of generators generating extra lines
                               #   for later in initxxx() -- for recursive
                               #   objects
        self.globaldecl = []
        self.globalobjects = []
        self.pendingfunctions = []
        self.debugstack = ()  # linked list of nested nameof()

        # special constructors:
        self.has_listarg = {}
        for name in "newtuple newlist newdict newstring".split():
            self.has_listarg[name] = name

        self.space = StdObjSpace() # for introspection

        # debugging
        global _gen; _gen = self
        
        self.gen_source()            
        
    def nameof(self, obj, debug=None):
        key = Constant(obj).key
        try:
            return self.rpynames[key]
        except KeyError:
            if debug:
                stackentry = debug, obj
            else:
                stackentry = obj
            self.debugstack = (self.debugstack, stackentry)
            if (type(obj).__module__ != '__builtin__' and
                not isinstance(obj, type)):   # skip user-defined metaclasses
                # assume it's a user defined thingy
                name = self.nameof_instance(obj)
            else:
                for cls in type(obj).__mro__:
                    meth = getattr(self,
                                   'nameof_' + cls.__name__.replace(' ', ''),
                                   None)
                    if meth:
                        break
                else:
                    raise Exception, "nameof(%r)" % (obj,)
                name = meth(obj)
            self.debugstack, x = self.debugstack
            assert x is stackentry
            self.rpynames[key] = name
            return name

    def uniquename(self, basename):
        basename = basename.translate(C_IDENTIFIER)
        n = self.seennames.get(basename, 0)
        self.seennames[basename] = n+1
        if n == 0:
            self.globalobjects.append(basename)
            self.globaldecl.append('# global object %s' % (basename,))
            return basename
        else:
            return self.uniquename('%s_%d' % (basename, n))

    def nameof_object(self, value):
        if type(value) is not object:
            raise Exception, "nameof(%r) in %r" % (value, self.current_func)
        name = self.uniquename('g_object')
        self.initcode.append('%s = object()'%name)
        return name

    def nameof_module(self, value):
        assert value is os or not hasattr(value, "__file__") or \
               not (value.__file__.endswith('.pyc') or
                    value.__file__.endswith('.py') or
                    value.__file__.endswith('.pyo')), \
               "%r is not a builtin module (probably :)"%value
        name = self.uniquename('mod%s'%value.__name__)
        self.initcode.append('import %s as _tmp' % value.__name__)
        self.initcode.append('%s = space.wrap(_tmp)' % (name))
        return name
        

    def nameof_int(self, value):
        if value >= 0:
            name = 'gi_%d' % value
        else:
            name = 'gim_%d' % abs(value)
        name = self.uniquename(name)
        self.initcode.append('%s = space.newint(%d)' % (name, value))
        return name

    def nameof_long(self, value):
    	# allow short longs only, meaning they
    	# must fit into a word.
    	assert (sys.maxint*2+1)&value==value, "your literal long is too long"
        # assume we want them in hex most of the time
        if value < 256L:
            s = "%dL" % value
        else:
            s = "0x%08xL" % value
        if value >= 0:
            name = 'glong_%s' % s
        else:
            name = 'glongm_%d' % abs(value)
        name = self.uniquename(name)
        self.initcode.append('%s = space.wrap(%s) # XXX implement long!' % (name, s))
        return name

    def nameof_float(self, value):
        name = 'gfloat_%s' % value
        name = (name.replace('-', 'minus')
                    .replace('.', 'dot'))
        name = self.uniquename(name)
        self.initcode.append('%s = space.newfloat(%r)' % (name, value))
        return name
    
    def nameof_str(self, value):
        if [c for c in value if c<' ' or c>'~' or c=='"' or c=='\\']:
            # non-printable string
            namestr = repr(value)[1:-1]
        else:
            # printable string
            namestr = value
        if not namestr:
            namestr = "_emptystr_"
        name = self.uniquename('gs_' + namestr[:32])
        self.initcode.append('%s = space.newstring(%r)' % (name, value))
        return name

    def skipped_function(self, func):
        # debugging only!  Generates a placeholder for missing functions
        # that raises an exception when called.
        name = self.uniquename('gskippedfunc_' + func.__name__)
        self.globaldecl.append('# global decl %s' % (name, name))
        self.initcode.append('# build func %s' % name)
        return name

    def nameof_function(self, func):
        printable_name = '(%s:%d) %s' % (
            func.func_globals.get('__name__', '?'),
            func.func_code.co_firstlineno,
            func.__name__)
        if self.translator.frozen:
            if func not in self.translator.flowgraphs:
                print "NOT GENERATING", printable_name
                return self.skipped_function(func)
        else:
            if (func.func_doc and
                func.func_doc.lstrip().startswith('NOT_RPYTHON')):
                print "skipped", printable_name
                return self.skipped_function(func)
        name = func.__name__
        name = self.uniquename('gfunc_' + func.__name__)
        f_name = 'f_' + name[6:]
        self.initcode.append('%s = interp2app(%s)' % (name, f_name))
        self.pendingfunctions.append(func)
        return name

    def nameof_staticmethod(self, sm):
        # XXX XXX XXXX
        func = sm.__get__(42.5)
        name = self.uniquename('gsm_' + func.__name__)
        functionname = self.nameof(func)
        self.initcode.append('INITCHK(%s = PyCFunction_New('
                             '&ml_%s, NULL))' % (name, functionname))
        return name

    def nameof_instancemethod(self, meth):
        if meth.im_self is None:
            # no error checking here
            return self.nameof(meth.im_func)
        else:
            ob = self.nameof(meth.im_self)
            func = self.nameof(meth.im_func)
            typ = self.nameof(meth.im_class)
            name = self.uniquename('gmeth_'+meth.im_func.__name__)
            self.initcode.append(
                '%s = 42# what?gencfunc_descr_get(%s, %s, %s))'%(
                name, func, ob, typ))
            return name

    def should_translate_attr(self, pbc, attr):
        ann = self.translator.annotator
        if ann is None:
            ignore = getattr(pbc.__class__, 'NOT_RPYTHON_ATTRIBUTES', [])
            if attr in ignore:
                return False
            else:
                return "probably"   # True
        classdef = ann.getuserclasses().get(pbc.__class__)
        if classdef and classdef.about_attribute(attr) is not None:
            return True
        return False

    def later(self, gen):
        self.latercode.append((gen, self.debugstack))

    def nameof_instance(self, instance):
        name = self.uniquename('ginst_' + instance.__class__.__name__)
        cls = self.nameof(instance.__class__)
        def initinstance():
            content = instance.__dict__.items()
            content.sort()
            for key, value in content:
                if self.should_translate_attr(instance, key):
                    yield 'space.setattr(%s, %s, %s)' % (
                        name, self.nameof(key), self.nameof(value))
        self.initcode.append('# how? INITCHK(SETUP_INSTANCE(%s, %s))' % (
            name, cls))
        self.later(initinstance())
        return name

    def nameof_builtin_function_or_method(self, func):
        if func.__self__ is None:
            # builtin function
            if hasattr(self.space, func.__name__):
                return "space.%s" % func.__name__
            # where does it come from? Python2.2 doesn't have func.__module__
            for modname, module in sys.modules.items():
                if hasattr(module, '__file__'):
                    if (module.__file__.endswith('.py') or
                        module.__file__.endswith('.pyc') or
                        module.__file__.endswith('.pyo')):
                        continue    # skip non-builtin modules
                if func is getattr(module, func.__name__, None):
                    break
            else:
                raise Exception, '%r not found in any built-in module' % (func,)
            name = self.uniquename('gbltin_' + func.__name__)
            if modname == '__builtin__':
                self.initcode.append('%s = space.getattr(space.w_builtin, %s)'% (
                    name, self.nameof(func.__name__)))
            else:
                self.initcode.append('%s = space.getattr(%s, %s)' % (
                    name, self.nameof(module), self.nameof(func.__name__)))
        else:
            # builtin (bound) method
            name = self.uniquename('gbltinmethod_' + func.__name__)
            self.initcode.append('%s = space.getattr(%s, %s)' % (
                name, self.nameof(func.__self__), self.nameof(func.__name__)))
        return name

    def nameof_classobj(self, cls):
        if cls.__doc__ and cls.__doc__.lstrip().startswith('NOT_RPYTHON'):
            raise Exception, "%r should never be reached" % (cls,)

        metaclass = "space.w_type"
        if issubclass(cls, Exception):
            if cls.__module__ == 'exceptions':
                return 'space.w_%s'%cls.__name__
            #else:
            #    # exceptions must be old-style classes (grr!)
            #    metaclass = "&PyClass_Type"
        # For the moment, use old-style classes exactly when the
        # pypy source uses old-style classes, to avoid strange problems.
        if not isinstance(cls, type):
            assert type(cls) is type(Exception)
            metaclass = "space.type(space.w_Exception)"

        name = self.uniquename('gcls_' + cls.__name__)
        basenames = [self.nameof(base) for base in cls.__bases__]
        def initclassobj():
            content = cls.__dict__.items()
            content.sort()
            for key, value in content:
                if key.startswith('__'):
                    if key in ['__module__', '__doc__', '__dict__',
                               '__weakref__', '__repr__', '__metaclass__']:
                        continue
                    # XXX some __NAMES__ are important... nicer solution sought
                    #raise Exception, "unexpected name %r in class %s"%(key, cls)
                if isinstance(value, staticmethod) and value.__get__(1) not in self.translator.flowgraphs and self.translator.frozen:
                    print value
                    continue
                if isinstance(value, FunctionType) and value not in self.translator.flowgraphs and self.translator.frozen:
                    print value
                    continue
                    
                yield 'space.setattr(%s, %s, %s)' % (
                    name, self.nameof(key), self.nameof(value))

        baseargs = ", ".join([self.nameof(basename) for basename in basenames])
        self.initcode.append('%s = space.call(%s, space.newtuple(\n'
                             '        [%s, space.newtuple([%s]), space.newdict([])]))'
                             %(name, metaclass, self.nameof(cls.__name__), baseargs))
        
        self.later(initclassobj())
        return name

    nameof_class = nameof_classobj   # for Python 2.2

    typename_mapping = {
        object: 'space.w_object',
        int:    'space.w_int',
        long:   'space.w_long',
        bool:   'space.w_bool',
        list:   'space.w_list',
        tuple:  'space.w_tuple',
        dict:   'space.w_dict',
        str:    'space.w_str',
        float:  'space.w_float',
        type(Exception()): 'space.wrap(types.InstanceType)',
        type:   'space.w_type',
        complex:'space.wrap(types.ComplexType)',
        unicode:'space.w_unicode',
        file:   'space.wrap(file)',
        type(None): 'space.wrap(types.NoneType)',
        CodeType: 'space.wrap(types.CodeType)',

        ##r_int:  'space.w_int',
        ##r_uint: 'space.w_int',

        # XXX we leak 5 references here, but that's the least of the
        #     problems with this section of code
        # type 'builtin_function_or_method':
        type(len): 'space.wrap(types.FunctionType)',
        # type 'method_descriptor':
        # XXX small problem here:
        # XXX with space.eval, we get <W_TypeObject(method)>
        # XXX but with wrap, we get <W_TypeObject(instancemethod)>
        type(list.append): 'eval_helper(space, "list.append")',
        # type 'wrapper_descriptor':
        type(type(None).__repr__): 'eval_helper(space, ".type(None).__repr__")',
        # type 'getset_descriptor':
        # XXX here we get <W_TypeObject(FakeDescriptor)>,
        # while eval gives us <W_TypeObject(GetSetProperty)>
        type(type.__dict__['__dict__']): 'eval_helper(space,'\
            ' "type(type.__dict__[\'__dict__\']))',
        # type 'member_descriptor':
        # XXX this does not work in eval!
        type(type.__dict__['__basicsize__']): "cannot eval type(type.__dict__['__basicsize__'])",
        }

    def nameof_type(self, cls):
        if cls in self.typename_mapping:
            return self.typename_mapping[cls]
        assert cls.__module__ != '__builtin__', \
            "built-in class %r not found in typename_mapping" % (cls,)
        return self.nameof_classobj(cls)

    def nameof_tuple(self, tup):
        name = self.uniquename('g%dtuple' % len(tup))
        args = [self.nameof(x) for x in tup]
        args = ', '.join(args)
        self.initcode.append('%s = space.newtuple([%s])' % (name, args))
        return name

    def nameof_list(self, lis):
        name = self.uniquename('g%dlist' % len(lis))
        def initlist():
            for i in range(len(lis)):
                item = self.nameof(lis[i])
                yield 'space.setitem(%s, %s, %s);' % (
                    name, self.nameof(i), self.nameof(item))
        self.initcode.append('%s = space.newlist(%s)' % (name, self.nameof(0)))
        self.initcode.append('%s = space.mul(%s, %s)' % (name, name, self.nameof(len(lis))))
        self.later(initlist())
        return name

    def nameof_dict(self, dic):
        assert dic is not __builtins__
        assert '__builtins__' not in dic, 'Seems to be the globals of %s' % (
            dic.get('__name__', '?'),)
        name = self.uniquename('g%ddict' % len(dic))
        def initdict():
            for k in dic:
                yield ('space.setitem(%s, %s, %s)'%(
                            name, self.nameof(k), self.nameof(dic[k])))
        self.initcode.append('%s = space.newdict([])' % (name,))
        self.later(initdict())
        return name

    # strange prebuilt instances below, don't look too closely
    # XXX oh well.
    def nameof_member_descriptor(self, md):
        name = self.uniquename('gdescriptor_%s_%s' % (
            md.__objclass__.__name__, md.__name__))
        cls = self.nameof(md.__objclass__)
        # do I need to take the dict and then getitem???
        self.initcode.append('%s = space.getattr(%s, %s)' %
                                (name, cls, self.nameof(md.__name__)))
        return name
    nameof_getset_descriptor  = nameof_member_descriptor
    nameof_method_descriptor  = nameof_member_descriptor
    nameof_wrapper_descriptor = nameof_member_descriptor

    def nameof_file(self, fil):
        if fil is sys.stdin:
            return '#XXX how: PySys_GetObject("stdin")'
        if fil is sys.stdout:
            return '#XXX how: PySys_GetObject("stdout")'
        if fil is sys.stderr:
            return '#XXX how: PySys_GetObject("stderr")'
        raise Exception, 'Cannot translate an already-open file: %r' % (fil,)

    def gen_source(self):
        f = self.f
        info = {
            'modname': self.modname,
            'entrypointname': self.translator.functions[0].__name__,
            'entrypoint': self.nameof(self.translator.functions[0]),
            }
        # header
        print >> f, self.RPY_HEADER

        # function implementations
        while self.pendingfunctions:
            func = self.pendingfunctions.pop()
            self.gen_rpyfunction(func)
            # collect more of the latercode after each function
            while self.latercode:
                gen, self.debugstack = self.latercode.pop()
                #self.initcode.extend(gen) -- eats TypeError! bad CPython!
                for line in gen:
                    self.initcode.append(line)
                self.debugstack = ()
            self.gen_global_declarations()

        # footer
        print >> f, self.RPY_INIT_HEADER % info
        if self.f2name is not None:
            print >> f, '    execfile("%s")' % self.f2name
        for codelines in self.initcode:
            for codeline in codelines.split("\n"):
                print >> f, "    %s" % codeline
        print >> f, self.RPY_INIT_FOOTER % info

    def gen_global_declarations(self):
        g = self.globaldecl
        if g:
            f = self.f
            print >> f, '# global declaration%s' % ('s'*(len(g)>1))
            for line in g:
                print >> f, line
            print >> f
            del g[:]
        g = self.globalobjects
        for name in g:
            pass # self.initcode.append('# REGISTER_GLOBAL(%s)' % (name,))
        del g[:]
        if self.f2 is not None:
            for line in self.initcode:
                print >> self.f2, line
            del self.initcode[:]

    def gen_rpyfunction(self, func):

        f = self.f
        body = list(self.rpyfunction_body(func))
        name_of_defaults = [self.nameof(x, debug=('Default argument of', func))
                            for x in (func.func_defaults or ())]
        self.gen_global_declarations()

        # print header
        cname = self.nameof(func)
        assert cname.startswith('gfunc_')
        f_name = 'f_' + cname[6:]

        # collect all the local variables
        graph = self.translator.getflowgraph(func)
        localslst = []
        def visit(node):
            if isinstance(node, Block):
                localslst.extend(node.getvariables())
        traverse(visit, graph)
        localnames = [a.name for a in uniqueitems(localslst)]

        # collect all the arguments
        if func.func_code.co_flags & CO_VARARGS:
            vararg = graph.getargs()[-1]
            positional_args = graph.getargs()[:-1]
        else:
            vararg = None
            positional_args = graph.getargs()
        min_number_of_args = len(positional_args) - len(name_of_defaults)

        fast_args = [a.name for a in positional_args]
        if vararg is not None:
            fast_args.append(str(vararg))
        fast_name = 'fast' + f_name

        fast_set = dict(zip(fast_args, fast_args))

        declare_fast_args = [('PyObject *' + a) for a in fast_args]
        if declare_fast_args:
            declare_fast_args = 'TRACE_ARGS ' + ', '.join(declare_fast_args)
        else:
            declare_fast_args = 'TRACE_ARGS_VOID'
        fast_function_header = ('static PyObject *\n'
                                '%s(%s)' % (fast_name, declare_fast_args))

        print >> f, fast_function_header + ';'  # forward
        print >> f

        print >> f, 'static PyObject *'
        print >> f, '%s(PyObject* self, PyObject* args, PyObject* kwds)' % (
            f_name,)
        print >> f, '{'
        print >> f, '\tFUNCTION_HEAD(%s, %s, args, %s, __FILE__, __LINE__ - 2)' % (
            c_string('%s(%s)' % (cname, ', '.join(name_of_defaults))),
            cname,
            '(%s)' % (', '.join(map(c_string, name_of_defaults) + ['NULL']),),
        )

        kwlist = ['"%s"' % name for name in
                      func.func_code.co_varnames[:func.func_code.co_argcount]]
        kwlist.append('0')
        print >> f, '\tstatic char* kwlist[] = {%s};' % (', '.join(kwlist),)

        if fast_args:
            print >> f, '\tPyObject *%s;' % (', *'.join(fast_args))
        print >> f

        print >> f, '\tFUNCTION_CHECK()'

        # argument unpacking
        if vararg is not None:
            print >> f, '\t%s = PyTuple_GetSlice(args, %d, INT_MAX);' % (
                vararg, len(positional_args))
            print >> f, '\tif (%s == NULL)' % (vararg,)
            print >> f, '\t\tFUNCTION_RETURN(NULL)'
            print >> f, '\targs = PyTuple_GetSlice(args, 0, %d);' % (
                len(positional_args),)
            print >> f, '\tif (args == NULL) {'
            print >> f, '\t\tERR_DECREF(%s)' % (vararg,)
            print >> f, '\t\tFUNCTION_RETURN(NULL)'
            print >> f, '\t}'
            tail = """{
\t\tERR_DECREF(args)
\t\tERR_DECREF(%s)
\t\tFUNCTION_RETURN(NULL);
\t}
\tPy_DECREF(args);""" % vararg
        else:
            tail = '\n\t\tFUNCTION_RETURN(NULL)'
        for i in range(len(name_of_defaults)):
            print >> f, '\t%s = %s;' % (
                positional_args[min_number_of_args+i],
                name_of_defaults[i])
        fmt = 'O'*min_number_of_args
        if min_number_of_args < len(positional_args):
            fmt += '|' + 'O'*(len(positional_args)-min_number_of_args)
        lst = ['args', 'kwds',
               '"%s:%s"' % (fmt, func.__name__),
               'kwlist',
               ]
        lst += ['&' + a.name for a in positional_args]
        print >> f, '\tif (!PyArg_ParseTupleAndKeywords(%s))' % ', '.join(lst),
        print >> f, tail

        call_fast_args = list(fast_args)
        if call_fast_args:
            call_fast_args = 'TRACE_CALL ' + ', '.join(call_fast_args)
        else:
            call_fast_args = 'TRACE_CALL_VOID'
        print >> f, '\treturn %s(%s);' % (fast_name, call_fast_args)
        print >> f, '}'
        print >> f

        print >> f, fast_function_header
        print >> f, '{'

        fast_locals = [arg for arg in localnames if arg not in fast_set]
        if fast_locals:
            print >> f, '\tPyObject *%s;' % (', *'.join(fast_locals),)
            print >> f
        
        # generate an incref for each input argument
        # skipped

        # print the body
        for line in body:
            print >>f, line

        # print the PyMethodDef
        # skipped

        if not self.translator.frozen:
            # this is only to keep the RAM consumption under control
            del self.translator.flowgraphs[func]
            Variable.instances.clear()

    def rpyfunction_body(self, func):
        try:
            graph = self.translator.getflowgraph(func)
        except Exception, e:
            print 20*"*", e
            print func
            raise
        # not needed, tuple assignment
        # remove_direct_loops(graph)
        checkgraph(graph)

        blocknum = {}
        allblocks = []
        localnames = {}

        def expr(v, wrapped = True):
            if isinstance(v, Variable):
                n = v.name
                if n.startswith("v") and n[1:].isdigit():
                    ret = localnames.get(v.name)
                    if not ret:
                        if wrapped:
                            localnames[v.name] = ret = "w_%d" % len(localnames)
                        else:
                            localnames[v.name] = ret = "v%d" % len(localnames)
                    return ret
            elif isinstance(v, Constant):
                return self.nameof(v.value,
                                   debug=('Constant in the graph of',func))
            else:
                raise TypeError, "expr(%r)" % (v,)

        def arglist(args):
            res = [expr(arg) for arg in args]
            return ", ".join(res)
        
        def oper(op):
            if op.opname == "simple_call":
                v = op.args[0]
                exv = expr(v)
                if exv.startswith("space.") and not exv.startswith("space.w_"):
                    # it is a space method
                    fmt = "%s = %s(%s)"
                else:
                    if isinstance(v, Constant) and v.value in self.translator.flowgraphs:
                        fmt = "%s = %s(space, %s)"
                    else:
                        fmt = "%s = space.call(%s, space.newtuple([%s]))"
                return fmt % (expr(op.result), expr(v), arglist(op.args[1:]))                    
            if op.opname in self.has_listarg:
                fmt = "%s = %s([%s])"
            else:
                fmt = "%s = %s(%s)"
            # specialcase is_true
            wrapped = op.opname != "is_true"
            oper = "space.%s" % op.opname
            return fmt % (expr(op.result, wrapped), oper, arglist(op.args))

        def large_assignment(left, right, margin=65):
            expr = "(%s) = (%s)" % (", ".join(left), ", ".join(right))
            pieces = expr.split(",")
            res = [pieces.pop(0)]
            for piece in pieces:
                if len(res[-1])+len(piece)+1 > margin:
                    res[-1] += ","
                    res.append(piece)
                else:
                    res[-1] += (","+piece)
            return res

        def gen_link(link, linklocalvars=None):
            "Generate the code to jump across the given Link."
            linklocalvars = linklocalvars or {}
            left, right = [], []
            for a1, a2 in zip(link.args, link.target.inputargs):
                if a1 in linklocalvars:
                    src = linklocalvars[a1]
                else:
                    src = expr(a1)
                left.append(expr(a2))
                right.append(src)
            txt = "%s = %s" % (", ".join(left), ", ".join(right))
            if len(txt) <= 65: # arbitrary
                yield txt
            else:
                for line in large_assignment(left, right):
                    yield line
            goto = blocknum[link.target]
            yield 'goto = %d' % goto
            if goto <= blocknum[block]:
                yield 'continue'
        
        f = self.f
        t = self.translator
        #t.simplify(func)
        graph = t.getflowgraph(func)

        start = graph.startblock
        allblocks = ordered_blocks(graph)
        nblocks = len(allblocks)

        blocknum = {}
        for block in allblocks:
            blocknum[block] = len(blocknum)+1

        # create function declaration
        name = func.__name__  # change this
        args = [expr(var) for var in start.inputargs]
        argstr = ", ".join(args)
        yield "def %s(space, %s):" % (name, argstr)
        yield "    goto = %d # startblock" % blocknum[start]
        yield "    while True:"
                
        def render_block(block):
            catch_exception = block.exitswitch == Constant(last_exception)
            regular_op = len(block.operations) - catch_exception
            # render all but maybe the last op
            for op in block.operations[:regular_op]:
                yield "%s" % oper(op)
            # render the last op if it is exception handled
            for op in block.operations[regular_op:]:
                yield "try:"
                yield "    %s" % oper(op)

            if len(block.exits) == 0:
                if len(block.inputargs) == 2:   # exc_cls, exc_value
                    # exceptional return block
                    exc_cls = expr(block.inputargs[0])
                    exc_val = expr(block.inputargs[1])
                    yield "raise OperationError(%s, %s)" % (exc_cls, exc_val)
                else:
                    # regular return block
                    retval = expr(block.inputargs[0])
                    yield "return %s" % retval
                return
            elif block.exitswitch is None:
                # single-exit block
                assert len(block.exits) == 1
                for op in gen_link(block.exits[0]):
                    yield "%s" % op
            elif catch_exception:
                # block catching the exceptions raised by its last operation
                # we handle the non-exceptional case first
                link = block.exits[0]
                assert link.exitcase is None
                for op in gen_link(link):
                    yield "    %s" % op
                # we must catch the exception raised by the last operation,
                # which goes to the last err%d_%d label written above.
                # Since we only have OperationError, we need to select:
                yield "except OperationError, e:"
                q = "if"
                for link in block.exits[1:]:
                    assert issubclass(link.exitcase, Exception)
                    # Exeption classes come unwrapped in link.exitcase
                    yield "    %s space.issubtype(e.w_type, %s):" % (q,
                                            self.nameof(link.exitcase))
                    q = "elif"
                    for op in gen_link(link, {
                                Constant(last_exception): 'e.w_type',
                                Constant(last_exc_value): 'e.w_value'}):
                        yield "        %s" % op
                yield "    else:raise # unhandled case, should not happen"
            else:
                # block ending in a switch on a value
                exits = list(block.exits)
                if len(exits) == 2 and (
                    exits[0].exitcase is False and exits[1].exitcase is True):
                    # order these guys like Python does
                    exits.reverse()
                q = "if"
                for link in exits[:-1]:
                    yield "%s %s == %s:" % (q, expr(block.exitswitch),
                                                     link.exitcase)
                    for op in gen_link(link):
                        yield "    %s" % op
                    q = "elif"
                link = exits[-1]
                yield "else:"
                yield "    assert %s == %s" % (expr(block.exitswitch),
                                                    link.exitcase)
                for op in gen_link(exits[-1]):
                    yield "    %s" % op

        for block in allblocks:
            blockno = blocknum[block]
            yield ""
            yield "        if goto == %d:" % blockno
            for line in render_block(block):
                yield "            %s" % line

# ____________________________________________________________

    RPY_HEADER = '#!/bin/env python\n# -*- coding: LATIN-1 -*-'

    RPY_SEP = "#*************************************************************"

    RPY_INIT_HEADER = RPY_SEP + '''

# something needed here? MODULE_INITFUNC(%(modname)s)
'''

    RPY_INIT_FOOTER = '''
# entry point: %(entrypointname)s, %(entrypoint)s)
'''

# a translation table suitable for str.translate() to remove
# non-C characters from an identifier
C_IDENTIFIER = ''.join([(('0' <= chr(i) <= '9' or
                          'a' <= chr(i) <= 'z' or
                          'A' <= chr(i) <= 'Z') and chr(i) or '_')
                        for i in range(256)])



def somefunc(arg):
    pass

def f(a,b):
    print "start"
    a = []
    a.append(3)
    for i in range(3):
        print i
    if a > b:
        try:
            if b == 123:
                raise ValueError
            elif b == 321:
                raise IndexError
            return 123
        except ValueError:
            raise TypeError
    else:
        dummy = somefunc(23)
        return 42

def ff(a, b):
    try:
        raise SystemError, 42
        return a+b
    finally:
        a = 7

glob = 100
def fff():
    global glob
    return 42+glob

def app_mod__String_ANY(format, values):
    import _formatting
    if isinstance(values, tuple):
        return _formatting.format(format, values, None)
    else:
        if hasattr(values, 'keys'):
            return _formatting.format(format, (values,), values)
        else:
            return _formatting.format(format, (values,), None)

def app_str_decode__String_ANY_ANY(str, encoding=None, errors=None):
    if encoding is None and errors is None:
        return unicode(str)
    elif errors is None:
        return unicode(str, encoding)
    else:
        return unicode(str, encoding, errors)
        

def test_md5():
    #import md5
    # how do I avoid the builtin module?
    from pypy.appspace import md5
    digest = md5.new("hello")

def test_mod():
    return app_mod__String_ANY("-%s-", ["hallo"])

def test_join():
    return " ".join(["hi", "there"])

entry_point = (f, ff, fff, app_str_decode__String_ANY_ANY, test_mod, test_md5, test_join) [5]

import os, sys
from pypy.interpreter import autopath
srcdir = os.path.dirname(autopath.pypydir)
appdir = os.path.join(autopath.pypydir, 'appspace')

if appdir not in sys.path:
    sys.path.insert(0, appdir)
t = Translator(entry_point, verbose=False, simplifying=True)
if 0:
    gen = GenRpy(sys.stdout, t)
else:
    fil= file("d:/tmp/look.py", "w")
    gen = GenRpy(fil, t)
    print >> fil, \
"""
from pypy.objspace.std import StdObjSpace
space = StdObjSpace()
test_mod(space)
"""
    fil.close()

#t.simplify()
#t.view()
# debugging
graph = t.getflowgraph()
ab = ordered_blocks(graph) # use ctrl-b in PyWin with ab

## testing how to call things
def f(space, w_a, w_b):
	return space.add(w_a, w_b)

space = gen.space
w = space.wrap
gw_f = interp2app(f)
w_gw_f = w(gw_f)
res = space.call(w_gw_f, space.newlist([w(2), w(3)]))
print res