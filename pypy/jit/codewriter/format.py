import py
from pypy.objspace.flow.model import Constant
from pypy.jit.codewriter.flatten import SSARepr, Label, TLabel, Register
from pypy.jit.codewriter.flatten import ListOfKind, SwitchDictDescr
from pypy.jit.metainterp.history import AbstractDescr


def format_assembler(ssarepr):
    """For testing: format a SSARepr as a multiline string."""
    from cStringIO import StringIO
    seen = {}
    #
    def repr(x):
        if isinstance(x, Register):
            return '%%%s%d' % (x.kind[0], x.index)    # e.g. %i1 or %r2 or %f3
        elif isinstance(x, Constant):
            return '$%r' % (x.value,)
        elif isinstance(x, TLabel):
            return getlabelname(x)
        elif isinstance(x, ListOfKind):
            return '%s[%s]' % (x.kind[0].upper(), ', '.join(map(repr, x)))
        elif isinstance(x, SwitchDictDescr):
            return '<SwitchDictDescr %s>' % (
                ', '.join(['%s:%s' % (key, getlabelname(lbl))
                           for key, lbl in x._labels]))
        elif isinstance(x, AbstractDescr):
            return '%r' % (x,)
        else:
            return '<unknown object: %r>' % (x,)
    #
    seenlabels = {}
    labelcount = [0]
    def getlabelname(lbl):
        if lbl.name not in seenlabels:
            labelcount[0] += 1
            seenlabels[lbl.name] = labelcount[0]
        return 'L%d' % seenlabels[lbl.name]
    #
    output = StringIO()
    for asm in ssarepr.insns:
        if isinstance(asm[0], Label):
            if asm[0].name in seenlabels:
                print >> output, '%s:' % getlabelname(asm[0])
        else:
            print >> output, asm[0],
            if len(asm) > 1:
                print >> output, ', '.join(map(repr, asm[1:]))
            else:
                print >> output
    res = output.getvalue()
    return res
