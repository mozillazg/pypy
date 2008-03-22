"""Dumps jitstates, frames, redboxes and containers as a .dot file.

Usage from a C-level debugger: call one the following global functions
with a pointer to the object in question as a single argument:

  * pypy_g_dump_jitstate()
  * pypy_g_dump_frame()
  * pypy_g_dump_redbox()
  * pypy_g_dump_container()

"""
import os
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.timeshifter import rvalue, rcontainer, vlist
from pypy.rlib.objectmodel import compute_unique_id as getid
from pypy.tool.pairtype import extendabletype

DUMPFILENAME = '%s.dot'


class GraphBuilder:

    def __init__(self):
        self.nodelines = []
        self.edgelines = []
        self.memo = rvalue.Memo()
        self.none_counter = 0
        self.seen_ids = {}

    def done(self, basename):
        lines = ['digraph %s {\n' % basename]
        lines += self.nodelines
        lines += self.edgelines
        lines.append('}\n')
        buf = ''.join(lines)
        filename = DUMPFILENAME % basename
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0644)
        while buf:
            count = os.write(fd, buf)
            buf = buf[count:]
        os.close(fd)
        print "Wrote dump to", filename

    def see(self, id):
        if id in self.seen_ids:
            return False
        else:
            self.seen_ids[id] = None
            return True

    def quote(self, s):
        s = '\\"'.join(s.split('"'))
        s = '\\n'.join(s.split('\n'))
        return s

    def iname(self, id):
        if id != 0:    # special support for edges pointing to None
            name = 'n_%x' % id
            name = name.replace('-', '_')
        else:
            name = 'None%d' % self.none_counter
            self.none_counter += 1
            self.nodelines.append('%s [label="None", color="#A0A0A0"];\n' %
                                  (name,))
        return name

    def emit_node(self, id, label, shape="box", fillcolor="", color=""):
        args = []
        args.append('label="%s"' % self.quote(label))
        args.append('shape="%s"' % shape)
        if fillcolor:
            args.append('fillcolor="%s"' % fillcolor)
        if color:
            args.append('color="%s"' % color)
        self.nodelines.append('%s [%s];\n' % (self.iname(id), ', '.join(args)))

    def emit_edge(self, id1, id2, label="", color="", weak=False):
        args = []
        if label:
            args.append('label="%s"' % self.quote(label))
        if color:
            args.append('color="%s"' % color)
        if weak:
            args.append('constraint=false')
        if args:
            args = '[%s]' % (', '.join(args),)
        else:
            args = ''
        self.edgelines.append('%s -> %s %s;\n' % (self.iname(id1),
                                                  self.iname(id2),
                                                  args))

    def add_jitstate(self, jitstate):
        if jitstate is None:
            return 0
        id = getid(jitstate)
        if self.see(id):
            text = str(jitstate)
            self.emit_edge(id, self.add_frame(jitstate.frame), color="red")
            self.emit_edge(id, self.add_redbox(jitstate.exc_type_box),
                           "exc_type")
            self.emit_edge(id, self.add_redbox(jitstate.exc_value_box),
                           "exc_value")
            for i in range(len(jitstate.virtualizables)):
                box = jitstate.virtualizables[i]
                self.emit_edge(id, self.add_redbox(box),
                               "virtualizables[%d]" % i)
            self.emit_node(id, text, fillcolor="#a5e6f0")
        return id

    def add_frame(self, frame):
        if frame is None:
            return 0
        id = getid(frame)
        if self.see(id):
            text = str(frame) + "\\n"
            if frame.bytecode is not None:
                text += "bytecode = '%s'\n" % frame.bytecode.name
                # XXX large nodes in dot are too annoying
                #self.emit_edge(id, self.add_bytecode(frame.bytecode),
                #               "bytecode")
            text += "pc = %d\n" % frame.pc
            if frame.backframe is not None:
                self.emit_edge(id, self.add_frame(frame.backframe),
                               color="red")
            for i in range(len(frame.local_boxes)):
                box = frame.local_boxes[i]
                self.emit_edge(id, self.add_redbox(box), "local_boxes[%d]" % i)
            self.emit_node(id, text, color="red", fillcolor="#ffd0d0")
        return id

    def add_bytecode(self, bytecode):
        if bytecode is None:
            return 0
        id = getid(bytecode)
        if self.see(id):
            if bytecode.dump_copy is not None:
                text = bytecode.dump_copy
            else:
                text = "JITCODE %s" % bytecode.name
            self.emit_node(id, text, color="red", fillcolor="#FFC0C0")
        return id

    def intgenvar(self, genvar):
        if genvar is None:
            return 'genvar=None'
        elif genvar.is_const:
            svalue = genvar.revealconst(lltype.Signed)
            uvalue = genvar.revealconst(lltype.Unsigned)
            return '%d (0x%x)' % (svalue, uvalue)
        else:
            return str(genvar)

    def doublegenvar(self, genvar):
        if genvar is None:
            return 'genvar=None'
        elif genvar.is_const:
            return str(genvar.revealconst(lltype.Float))
        else:
            return str(genvar)

    def ptrgenvar(self, genvar):
        if genvar is None:
            return 'genvar=None'
        elif genvar.is_const:
            return str(genvar.revealconst(llmemory.Address))
        else:
            return str(genvar)

    def add_redbox(self, redbox):
        if redbox is None:
            return 0
        id = getid(redbox)
        if self.see(id):
            text = "%s\\n%s" % (str(redbox), redbox._rdump(id, self))
            self.emit_node(id, text)
        return id

    def add_container(self, container):
        if container is None:
            return 0
        id = getid(container)
        if self.see(id):
            text = "%s\\n%s" % (str(container), container._rdump(id, self))
            self.emit_node(id, text, fillcolor="#ffff60", color="#808000")
        return id

# We need to avoid using isinstance(x, Cls) because it forces the
# Classes to be seen by the annotator even if the rest of the code is
# not using them; then it chokes because they don't have the attributes
# we are trying to read...

class __extend__(rvalue.RedBox):
    __metaclass__ = extendabletype
    def _rdump(self, id, gb):
        return gb.intgenvar(self.genvar)

class __extend__(rvalue.PtrRedBox):
    __metaclass__ = extendabletype
    def _rdump(self, id, gb):
        if self.content is not None:
            gb.emit_edge(id, gb.add_container(self.content))
            if self.genvar is None:
                return "virtual"
        return gb.ptrgenvar(self.genvar)

class __extend__(rvalue.DoubleRedBox):
    __metaclass__ = extendabletype
    def _rdump(self, id, gb):
        return gb.doublegenvar(self.genvar)


class __extend__(rcontainer.AbstractContainer):
    __metaclass__ = extendabletype
    def _rdump(self, id, gb):
        return ''

class __extend__(rcontainer.VirtualContainer):
    __metaclass__ = extendabletype
    def _rdump(self, id, gb):
        gb.emit_edge(id, gb.add_redbox(self.ownbox),
                     color="#808000", weak=True)
        return ''

class __extend__(rcontainer.VirtualStruct):
    __metaclass__ = extendabletype
    def _rdump(self, id, gb):
        rcontainer.VirtualContainer._rdump(self, id, gb)
        fielddescs = self.typedesc.fielddescs
        for i in range(len(self.content_boxes)):
            try:
                name = fielddescs[i].fieldname
            except IndexError:
                name = 'field out of bounds (%d)' % (i,)
            box = self.content_boxes[i]
            gb.emit_edge(id, gb.add_redbox(box), name)
        return self.typedesc.name

class __extend__(vlist.VirtualList):
    __metaclass__ = extendabletype
    def _rdump(self, id, gb):
        rcontainer.VirtualContainer._rdump(self, id, gb)
        for i in range(len(self.item_boxes)):
            box = self.item_boxes[i]
            gb.emit_edge(id, gb.add_redbox(box),
                           'item_boxes[%d]' % i)
        return 'length %d' % len(self.item_boxes)

# ____________________________________________________________
#
# Public API

def dump_jitstate(jitstate):
    gb = GraphBuilder()
    gb.add_jitstate(jitstate)
    gb.done("jitstate")

def dump_frame(frame):
    gb = GraphBuilder()
    gb.add_frame(frame)
    gb.done("frame")

def dump_redbox(redbox):
    gb = GraphBuilder()
    gb.add_redbox(redbox)
    gb.done("redbox")

def dump_container(container):
    gb = GraphBuilder()
    gb.add_container(container)
    gb.done("container")

# keep these functions non-inlined so that they are callable from gdb
dump_jitstate._dont_inline_ = True
dump_frame._dont_inline_ = True
dump_redbox._dont_inline_ = True
dump_container._dont_inline_ = True
