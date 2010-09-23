from pypy.jit.metainterp.optimizeopt.optimizer import *
from pypy.jit.metainterp.resoperation import rop, ResOperation

class OptInvariant(Optimization):
    """Move loop invariant code into a preamble.
    """
    def setup(self, virtuals):
        if not virtuals:
            return
        
        inputargs = self.optimizer.original_inputargs
        if not inputargs:
            return
        
        jump_op = self.optimizer.loop.operations[-1]
        assert(jump_op.opnum == rop.JUMP)
        #for arg_in, arg_out in zip(inputargs, jump_op.args):
        print
        print inputargs, jump_op.args
        for i in range(len(inputargs)):
            arg_in, arg_out = inputargs[i], jump_op.args[i]
            if arg_in is arg_out:
                print "Invariant: ", arg_in
                v = self.getvalue(arg_in)
                v.invariant = True
        self.invariant_boxes = []
        
    def propagate_forward(self, op):
    
        if op.opnum == rop.JUMP:
            loop = self.optimizer.loop
            if loop.preamble and len(self.optimizer.preamble)>0:
                preamble = loop.preamble
                preamble.inputargs = loop.inputargs[:]
                loop.inputargs.extend(self.invariant_boxes)
                op.args = op.args + self.invariant_boxes
                preamble.operations = self.optimizer.preamble
                preamble.token.specnodes = loop.token.specnodes
                jmp = ResOperation(rop.JUMP,
                                   loop.inputargs[:],
                                   None)
                jmp.descr = loop.token
                preamble.operations.append(jmp)

        elif (op.is_always_pure()):# or op.is_foldable_guard() or op.is_ovf()):
            if self.has_invariant_args(op):
                self.emit_invariant(op)
                return

        #elif op.is_guard_overflow():
        #    prev_op = self.optimizer.loop.operations[self.optimizer.i - 1]
        #    v = self.getvalue(prev_op.result)
        #    if v.invariant:
        #        self.emit_invariant(op)
        #        return
            
        self.emit_operation(op)

    def emit_invariant(self, op):
        print "P: ", op, op.opnum
        op.invariant = True
        self.emit_operation(op)
        if self.get_constant_box(op.result) is None:
            v = self.getvalue(op.result)
            v.invariant = True
            box = v.force_box() 
            if box and box not in self.invariant_boxes:
                self.invariant_boxes.append(box)
            
    def has_invariant_args(self, op):
        for a in op.args:
            if self.get_constant_box(a) is None:
                if a not in self.optimizer.values:
                    return False
                v = self.getvalue(a)
                if not v.invariant:
                    return False
        return True
        
