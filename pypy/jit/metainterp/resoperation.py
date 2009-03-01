
class ResOperation(object):
    """The central ResOperation class, representing one operation."""

    # for 'merge_point'
    specnodes = None
    key = None

    # for 'jump' and 'guard_*'
    jump_target = None

    # for 'guard_*'
    counter = 0
    storage_info = None
    liveboxes = None

    def __init__(self, opname, args, result):
        self.opname = opname
        self.args = list(args)
        self.result = result

    def __repr__(self):
        if self.result is not None:
            sres = repr(self.result) + ' = '
        else:
            sres = ''
        result = '%s%s(%s)' % (sres, self.opname,
                               ', '.join(map(repr, self.args)))
        if self.liveboxes is not None:
            result = '%s [%s]' % (result, ', '.join(map(repr, self.liveboxes)))
        return result

    def clone(self):
        op = ResOperation(self.opname, self.args, self.result)
        op.specnodes = self.specnodes
        op.key = self.key
        return op

# ____________________________________________________________

