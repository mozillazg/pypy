from pypy.jit.metainterp.optimizeopt.optimizer import *
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.compile import prebuiltNotSpecNode

class OptInvariant(Optimization):
    """Move loop invariant code into a preamble.
    """
    def setup(self, virtuals):
        if not virtuals:
            return
        
        #inputargs = self.optimizer.original_inputargs
        inputargs = self.optimizer.loop.inputargs
        if not inputargs:
            return
        
        jump_op = self.optimizer.loop.operations[-1]
        if jump_op.opnum != rop.JUMP:
            return 

        for i in range(len(inputargs)):
            arg_in, arg_out = inputargs[i], jump_op.args[i]
            if arg_in is arg_out:
                v = self.getvalue(arg_in)
                v.invariant = True

    def invariant_boxes(self):
        invariant_boxes = []
        for op in self.optimizer.preamble:
            if self.get_constant_box(op.result) is None:
                v = self.getvalue(op.result)
                v.invariant = True
                box = v.force_box() 
                if box and box not in invariant_boxes:
                    invariant_boxes.append(box)
        return invariant_boxes

    def propagate_forward(self, op):
    
        if op.opnum == rop.JUMP:
            loop = self.optimizer.loop
            if loop.preamble and len(self.optimizer.preamble)>0:
                # First trace through loop, create preamble
                self.emit_operation(op)
                preamble = loop.preamble
                preamble.inputargs = loop.inputargs[:]

                invariant_boxes = self.invariant_boxes()
                loop.inputargs.extend(invariant_boxes)
                op.args = op.args + invariant_boxes
                preamble.operations = self.optimizer.preamble
                preamble.token.specnodes = loop.token.specnodes 
                loop.token.specnodes = loop.token.specnodes + \
                                       [prebuiltNotSpecNode] * len(invariant_boxes)

                print
                print loop.token.number
                print len(loop.token.specnodes)
                jmp = ResOperation(rop.JUMP,
                                   loop.inputargs[:],
                                   None)
                jmp.descr = loop.token
                preamble.operations.append(jmp)
                preamble.token.preamble = preamble
                return

            elif op.descr.preamble:
                # Bridge calling a loop with preamble, inline it
                #
                print
                print "hi: ", op
                print loop
                print
                self.inline(op.descr.preamble, op.args)
                return

        elif (op.is_always_pure()):# or op.is_foldable_guard() or op.is_ovf()):
            if self.has_invariant_args(op):
                op.invariant = True
                self.emit_operation(op)
                if self.get_constant_box(op.result) is None:
                    v = self.getvalue(op.result)
                    v.invariant = True
                return


        #elif op.is_guard_overflow():
        #    prev_op = self.optimizer.loop.operations[self.optimizer.i - 1]
        #    v = self.getvalue(prev_op.result)
        #    if v.invariant:
        #        self.emit_invariant(op)
        #        return
            
        self.emit_operation(op)

    def has_invariant_args(self, op):
        for a in op.args:
            if self.get_constant_box(a) is None:
                if a not in self.optimizer.values:
                    return False
                v = self.getvalue(a)
                if not v.invariant:
                    return False
        return True

    def inline(self, loop, inputargs):
        argmap = {}
        for i in range(len(inputargs)):
           argmap[loop.inputargs[i]] = inputargs[i]
        for op in loop.operations:
            newop = op.clone()
            newop.args = [argmap[a] for a in op.args]
            if op.result:
                newop.result = op.result.clonebox()
                argmap[op.result] = newop.result
            self.emit_operation(newop)
        
        
