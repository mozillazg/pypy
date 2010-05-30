from pypy.jit.codewriter.flatten import Label

def optimize_ssarepr(ssarepr):
    # For now, just optimize "L2: goto L1" by moving the label L2
    # at the same place as L1, and possibly killing the "goto L1"
    # if it becomes unreachable.
    i = 0
    insns = ssarepr.insns
    while i < len(insns):
        if (isinstance(insns[i][0], Label) and
            insns[i+1][0] == 'goto'):
            movinglabelinsn = insns[i]
            targettlabel = insns[i+1][1]
            if movinglabelinsn[0].name != targettlabel.name:
                del insns[i]
                if i > 0:
                    if insns[i-1][0] == '---':
                        del insns[i]
                    else:
                        i -= 1
                targetindex = insns.index((Label(targettlabel.name),))
                insns.insert(targetindex, movinglabelinsn)
                continue
        i += 1
