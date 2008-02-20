# graph transformations for transforming the portal graph(s)

class PortalRewriter(object):
    def __init__(self, hintannotator, rtyper, RGenOp):
        self.hintannotator = hintannotator
        self.rtyper = rtyper
        self.RGenOp = RGenOp

    def rewrite(self, origportalgraph, view=False):
        self.origportalgraph = origportalgraph
        self.view = view
        self.readportalgraph = None
