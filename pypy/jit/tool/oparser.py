
""" Simplify optimize tests by allowing to write them
in a nicer fashion
"""

from pypy.jit.tool.oparser_model import get_model

from pypy.jit.metainterp.resoperation import rop, opclasses, rop_lowercase,\
     ResOpWithDescr, N_aryOp, UnaryOp, PlainResOp, create_resop_dispatch,\
     ResOpNone, create_resop_0, example_for_opnum, FLOAT
from pypy.jit.metainterp import optmodel
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.objectmodel import Symbolic

class ParseError(Exception):
    pass

class OpParser(object):

    use_mock_model = False

    def __init__(self, input, cpu, namespace, type_system,
                 invent_fail_descr=True, results=None, mutable=False):
        self.input = input
        self.vars = {}
        self.cpu = cpu
        self._consts = namespace
        self.type_system = type_system
        self.invent_fail_descr = invent_fail_descr
        self.model = get_model(self.use_mock_model)
        self.original_jitcell_token = self.model.JitCellToken()
        self.results = results
        self.mutable = mutable
        self.allops = []

    def get_const(self, name, typ):
        if self._consts is None:
            return name
        obj = self._consts[name]
        if self.type_system == 'lltype':
            if typ == 'ptr':
                return self.model.ConstPtr(obj)
            else:
                assert typ == 'class'
                if not isinstance(obj, Symbolic):
                    obj = self.model.ptr_to_int(obj)
                return self.model.ConstInt(obj)
        else:
            if typ == 'ptr':
                return self.model.ConstObj(obj)
            else:
                assert typ == 'class'
                return self.model.ConstObj(ootype.cast_to_object(obj))

    def get_descr(self, poss_descr, allow_invent):
        if poss_descr.startswith('<'):
            return None
        try:
            return self._consts[poss_descr]
        except KeyError:
            if allow_invent:
                int(poss_descr)
                token = self.model.JitCellToken()
                tt = self.model.TargetToken(token)
                self._consts[poss_descr] = tt
                return tt
            raise

    def parse_header_line(self, line):
        elements = line.split(",")
        vars = []
        for elem in elements:
            elem = elem.strip()
            vars.append(self.newvar(elem))
        return vars

    def newvar(self, elem):
        if elem not in self.vars:
            if elem[0] in 'ifp':
                if elem[0] == 'p':
                    p = 'r'
                else:
                    p = elem[0]
                opnum = getattr(rop, 'INPUT_' + p)
                box = create_resop_0(opnum, example_for_opnum(opnum),
                                     mutable=self.mutable)
            else:
                raise ParseError("Unknown variable type: %s" % elem)
            self.setstr(box, elem)
            self.vars[elem] = box
        return self.vars[elem]

    def is_float(self, arg):
        try:
            float(arg)
            return True
        except ValueError:
            return False

    def getvar(self, arg):
        if not arg:
            return self.model.ConstInt(0)
        try:
            return self.model.ConstInt(int(arg))
        except ValueError:
            if self.is_float(arg):
                return self.model.ConstFloat(self.model.convert_to_floatstorage(arg))
            if (arg.startswith('"') or arg.startswith("'") or
                arg.startswith('s"')):
                # XXX ootype
                info = arg[1:].strip("'\"")
                return self.model.get_const_ptr_for_string(info)
            if arg.startswith('u"'):
                # XXX ootype
                info = arg[1:].strip("'\"")
                return self.model.get_const_ptr_for_unicode(info)
            if arg.startswith('ConstClass('):
                name = arg[len('ConstClass('):-1]
                return self.get_const(name, 'class')
            elif arg == 'None':
                return None
            elif arg == 'NULL':
                if self.type_system == 'lltype':
                    return self.model.ConstPtr(self.model.ConstPtr.value)
                else:
                    return self.model.ConstObj(self.model.ConstObj.value)
            elif arg.startswith('ConstPtr('):
                name = arg[len('ConstPtr('):-1]
                return self.get_const(name, 'ptr')
            if arg not in self.vars:
                raise Exception("unexpected var %s" % (arg,))
            return self.vars[arg]

    def parse_args(self, opname, argspec):
        args = []
        descr = None
        if argspec.strip():
            allargs = [arg for arg in argspec.split(",")
                       if arg != '']

            poss_descr = allargs[-1].strip()
            if poss_descr.startswith('descr='):
                descr = self.get_descr(poss_descr[len('descr='):],
                                       opname == 'label')
                allargs = allargs[:-1]
            for arg in allargs:
                arg = arg.strip()
                try:
                    args.append(self.getvar(arg))
                except KeyError:
                    raise ParseError("Unknown var: %s" % arg)
        return args, descr

    def parse_op(self, line):
        num = line.find('(')
        if num == -1:
            raise ParseError("invalid line: %s" % line)
        opname = line[:num]
        try:
            opnum = getattr(rop_lowercase, opname)
        except AttributeError:
            raise ParseError("unknown op: %s" % opname)
        endnum = line.rfind(')')
        if endnum == -1:
            raise ParseError("invalid line: %s" % line)
        if line.find('[', endnum) >= 0:
            raise ParseError("fail_args should be removed: %s" % line)
        args, descr = self.parse_args(opname, line[num + 1:endnum])
        if descr is None and opnum == rop.JUMP:
            descr = self.original_jitcell_token
        return opnum, args, descr

    def create_op(self, opnum, result, args, descr):
        r = create_resop_dispatch(opnum, result, args, mutable=self.mutable)
        if descr is not None:
            r.setdescr(descr)
        return r

    def parse_result_op(self, line, num):
        res, op = line.split("=", 1)
        res = res.strip()
        op = op.strip()
        opnum, args, descr = self.parse_op(op)
        if res in self.vars:
            raise ParseError("Double assign to var %s in line: %s" % (res, line))
        if self.results is None:
            result = example_for_opnum(opnum)
        else:
            result = self.results[num]
        opres = self.create_op(opnum, result, args, descr)
        self.setstr(opres, res)
        self.vars[res] = opres
        return opres

    def setstr(self, op, text):
        op._str = text
        try:
            num = int(text[1:])
        except ValueError:
            num = -1
        if num >= 0:
            op._varindex = num
        self.allops.append(op)

    def parse_op_no_result(self, line):
        opnum, args, descr = self.parse_op(line)
        res = self.create_op(opnum, None, args, descr)
        return res

    def parse_next_op(self, line, num):
        if "=" in line and line.find('(') > line.find('='):
            return self.parse_result_op(line, num)
        else:
            return self.parse_op_no_result(line)

    def parse(self):
        lines = self.input.splitlines()
        ops = []
        newlines = []
        first_comment = None
        for line in lines:
            # for simplicity comments are not allowed on
            # debug_merge_point lines
            if '#' in line and 'debug_merge_point(' not in line:
                if line.lstrip()[0] == '#': # comment only
                    if first_comment is None:
                        first_comment = line
                    continue
                comm = line.rfind('#')
                rpar = line.find(')') # assume there's a op(...)
                if comm > rpar:
                    line = line[:comm].rstrip()
            if not line.strip():
                continue  # a comment or empty line
            newlines.append(line)
        base_indent, inpargs, newlines = self.parse_inpargs(newlines)
        num, ops, last_offset = self.parse_ops(base_indent, newlines, 0)
        if num < len(newlines):
            raise ParseError("unexpected dedent at line: %s" % newlines[num])
        assign_all_varindices(self.allops)
        loop = self.model.ExtendedTreeLoop("loop")
        loop.comment = first_comment
        loop.original_jitcell_token = self.original_jitcell_token
        loop.operations = ops
        loop.inputargs = inpargs
        loop.last_offset = last_offset
        return loop

    def parse_ops(self, indent, lines, start):
        num = start
        ops = []
        last_offset = None
        while num < len(lines):
            line = lines[num]
            if not line.startswith(" " * indent):
                # dedent
                return num, ops
            elif line.startswith(" "*(indent + 1)):
                raise ParseError("indentation not valid any more")
            else:
                line = line.strip()
                offset, line = self.parse_offset(line)
                if line == '--end of the loop--':
                    last_offset = offset
                else:
                    op = self.parse_next_op(line, len(ops))
                    if offset:
                        op.offset = offset
                    ops.append(op)
                num += 1
        return num, ops, last_offset

    def postprocess(self, loop):
        """ A hook that can be overloaded to do some postprocessing
        """
        return loop

    def parse_offset(self, line):
        if line.startswith('+'):
            # it begins with an offset, like: "+10: i1 = int_add(...)"
            offset, _, line = line.partition(':')
            offset = int(offset)
            return offset, line.strip()
        return None, line

    def parse_inpargs(self, lines):
        line = lines[0]
        base_indent = len(line) - len(line.lstrip(' '))
        line = line.strip()
        if not line.startswith('['):
            raise ParseError("error parsing %s as inputargs" % (line,))
        lines = lines[1:]
        if line == '[]':
            return base_indent, [], lines
        if not line.startswith('[') or not line.endswith(']'):
            raise ParseError("Wrong header: %s" % line)
        inpargs = self.parse_header_line(line[1:-1])
        return base_indent, inpargs, lines

DEFAULT = object()

def parse(input, cpu=None, namespace=DEFAULT, type_system='lltype',
          invent_fail_descr=True, OpParser=OpParser,
          results=None, mutable=False):
    if namespace is DEFAULT:
        namespace = {}
    return OpParser(input, cpu, namespace, type_system,
                    invent_fail_descr, results, mutable).parse()

def pure_parse(*args, **kwds):
    kwds['invent_fail_descr'] = False
    return parse(*args, **kwds)


def assign_all_varindices(allops):
    assigned_varindices = {}
    unassigned_varindices = []
    #
    for op in allops:
        if getattr(op, '_varindex', -1) >= 0:
            num = op._varindex
            assert num not in assigned_varindices, (
                "duplicate or overlapping var: %s and %s" % (
                op, assigned_varindices[num]))
            assigned_varindices[num] = op
            if op.type == FLOAT:
                assert (num + 1) not in assigned_varindices, (
                    "duplicate or overlapping var: %s and %s" % (
                    op, assigned_varindices[num + 1]))
                assigned_varindices[num + 1] = op
        else:
            unassigned_varindices.append(op)
    #
    nextindex = 0
    for op in unassigned_varindices:
        while (nextindex in assigned_varindices or
               (op.type == FLOAT and (nextindex + 1) in assigned_varindices)):
            nextindex += 1
        op._varindex = nextindex
        nextindex += 1
        if op.type == FLOAT:
            nextindex += 1
