import py
from pypy.objspace.flow.model import Constant
from pypy.jit.codewriter.flatten import SSARepr, Label, TLabel, Register


def format_assembler(ssarepr):
    """For testing: format a SSARepr as a multiline string."""
    from cStringIO import StringIO
    seen = {}
    #
    def repr(x):
        if isinstance(x, Register):
            return '%%%s%d' % (x.kind[0], x.index)    # e.g. %i1 or %r2 or %f3
        elif isinstance(x, Constant):
            return '$' + str(x.value)
        elif isinstance(x, TLabel):
            return getlabelname(x)
        elif isinstance(x, list):
            return '[%s]' % ', '.join(map(repr, x))
        else:
            return '<unknown object: %r>' % (x,)
    #
    seenlabels = {}
    for asm in ssarepr.insns:
        for x in asm:
            if isinstance(x, TLabel):
                seenlabels[x.name] = -1
    labelcount = [0]
    def getlabelname(lbl):
        if seenlabels[lbl.name] == -1:
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
    return output.getvalue()
