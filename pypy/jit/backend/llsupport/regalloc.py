
from pypy.jit.metainterp.history import Const, Box
from pypy.rlib.objectmodel import we_are_translated

class TempBox(Box):
    def __init__(self):
        pass

    def __repr__(self):
        return "<TempVar at %s>" % (id(self),)

class NoVariableToSpill(Exception):
    pass

class StackManager(object):
    """ Manage stack positions
    """
    def __init__(self):
        self.stack_bindings = {}
        self.stack_depth    = 0

    def get(self, box):
        return self.stack_bindings.get(box, None)

    def loc(self, box):
        res = self.get(box)
        if res is not None:
            return res
        newloc = self.stack_pos(self.stack_depth)
        self.stack_bindings[box] = newloc
        self.stack_depth += 1
        return newloc

    # abstract methods that need to be overwritten for specific assemblers
    def stack_pos(self, loc):
        raise NotImplementedError("Purely abstract")

class RegisterManager(object):
    """ Class that keeps track of register allocations
    """
    def __init__(self, register_pool, longevity, no_lower_byte_regs=(),
                 stack_manager=None, assembler=None):
        self.free_regs = register_pool[:]
        self.all_regs = register_pool
        self.longevity = longevity
        self.reg_bindings = {}
        self.position = 0
        self.no_lower_byte_regs = no_lower_byte_regs
        self.stack_manager = stack_manager
        self.assembler = assembler

    def next_instruction(self, incr=1):
        self.position += incr

    def possibly_free_var(self, v):
        if isinstance(v, Const) or v not in self.reg_bindings:
            return
        if v not in self.longevity or self.longevity[v][1] <= self.position:
            self.free_regs.append(self.reg_bindings[v])
            del self.reg_bindings[v]

    def possibly_free_vars(self, vars):
        for v in vars:
            self.possibly_free_var(v)

    def _check_invariants(self):
        if not we_are_translated():
            # make sure no duplicates
            assert len(dict.fromkeys(self.reg_bindings.values())) == len(self.reg_bindings)
            rev_regs = dict.fromkeys(self.reg_bindings.values())
            for reg in self.free_regs:
                assert reg not in rev_regs
            assert len(rev_regs) + len(self.free_regs) == len(self.all_regs)
        else:
            assert len(self.reg_bindings) + len(self.free_regs) == len(self.all_regs)
        if self.longevity:
            for v in self.reg_bindings:
                assert self.longevity[v][1] > self.position

    def try_allocate_reg(self, v, selected_reg=None, need_lower_byte=False):
        assert not isinstance(v, Const)
        if selected_reg is not None:
            res = self.reg_bindings.get(v, None)
            if res is not None:
                if res is selected_reg:
                    return res
                else:
                    del self.reg_bindings[v]
                    self.free_regs.append(res)
            if selected_reg in self.free_regs:
                self.free_regs = [reg for reg in self.free_regs
                                  if reg is not selected_reg]
                self.reg_bindings[v] = selected_reg
                return selected_reg
            return None
        if need_lower_byte:
            loc = self.reg_bindings.get(v, None)
            if loc is not None and loc not in self.no_lower_byte_regs:
                return loc
            for i in range(len(self.free_regs)):
                reg = self.free_regs[i]
                if reg not in self.no_lower_byte_regs:
                    if loc is not None:
                        self.free_regs[i] = loc
                    else:
                        del self.free_regs[i]
                    self.reg_bindings[v] = reg
                    return reg
            return None
        try:
            return self.reg_bindings[v]
        except KeyError:
            if self.free_regs:
                loc = self.free_regs.pop()
                self.reg_bindings[v] = loc
                return loc

    def _spill_var(self, v, forbidden_vars, selected_reg,
                   need_lower_byte=False):
        v_to_spill = self.pick_variable_to_spill(v, forbidden_vars,
                               selected_reg, need_lower_byte=need_lower_byte)
        loc = self.reg_bindings[v_to_spill]
        del self.reg_bindings[v_to_spill]
        if self.stack_manager.get(v_to_spill) is None:
            newloc = self.stack_manager.loc(v_to_spill)
            self.assembler.regalloc_mov(loc, newloc)
        return loc

    def pick_variable_to_spill(self, v, forbidden_vars, selected_reg=None,
                               need_lower_byte=False):
        """ Silly algorithm.
        """
        candidates = []
        for next in self.reg_bindings:
            reg = self.reg_bindings[next]
            if next in forbidden_vars:
                continue
            if selected_reg is not None:
                if reg is selected_reg:
                    return next
                else:
                    continue
            if need_lower_byte and reg in self.no_lower_byte_regs:
                continue
            return next
        raise NoVariableToSpill

    def force_allocate_reg(self, v, forbidden_vars=[], selected_reg=None,
                           need_lower_byte=False):
        if isinstance(v, TempBox):
            self.longevity[v] = (self.position, self.position)
        loc = self.try_allocate_reg(v, selected_reg,
                                    need_lower_byte=need_lower_byte)
        if loc:
            return loc
        loc = self._spill_var(v, forbidden_vars, selected_reg,
                              need_lower_byte=need_lower_byte)
        prev_loc = self.reg_bindings.get(v, None)
        if prev_loc is not None:
            self.free_regs.append(prev_loc)
        self.reg_bindings[v] = loc
        return loc

    def loc(self, box):
        if isinstance(box, Const):
            return self.convert_to_imm(box)
        try:
            return self.reg_bindings[box]
        except KeyError:
            return self.stack_manager.loc(box)

    def return_constant(self, v, forbidden_vars=[], selected_reg=None,
                        imm_fine=True):
        assert isinstance(v, Const)
        if selected_reg or not imm_fine:
            # this means we cannot have it in IMM, eh
            if selected_reg in self.free_regs:
                self.assembler.regalloc_mov(self.convert_to_imm(v), selected_reg)
                return selected_reg
            if selected_reg is None and self.free_regs:
                loc = self.free_regs.pop()
                self.assembler.regalloc_mov(self.convert_to_imm(v), loc)
                return loc
            loc = self._spill_var(v, forbidden_vars, selected_reg)
            self.free_regs.append(loc)
            self.Load(v, convert_to_imm(v), loc)
            return loc
        return convert_to_imm(v)

    def make_sure_var_in_reg(self, v, forbidden_vars=[], selected_reg=None,
                             imm_fine=True, need_lower_byte=False):
        if isinstance(v, Const):
            return self.return_constant(v, forbidden_vars, selected_reg,
                                        imm_fine)
        
        prev_loc = self.loc(v)
        loc = self.force_allocate_reg(v, forbidden_vars, selected_reg,
                                      need_lower_byte=need_lower_byte)
        if prev_loc is not loc:
            self.assembler.regalloc_mov(prev_loc, loc)
        return loc

    def reallocate_from_to(self, from_v, to_v):
        reg = self.reg_bindings[from_v]
        del self.reg_bindings[from_v]
        self.reg_bindings[to_v] = reg

    def move_variable_away(self, v, prev_loc):
        reg = None
        if self.free_regs:
            loc = self.free_regs.pop()
            self.reg_bindings[v] = loc
            self.assembler.regalloc_mov(prev_loc, loc)
        else:
            loc = self.stack_manager.loc(v)
            self.assembler.regalloc_mov(prev_loc, loc)

    def force_result_in_reg(self, result_v, v, forbidden_vars=[]):
        """ Make sure that result is in the same register as v
        and v is copied away if it's further used
        """
        if isinstance(v, Const):
            loc = self.make_sure_var_in_reg(v, forbidden_vars,
                                            imm_fine=False)
            self.reg_bindings[result_v] = loc
            self.free_regs = [reg for reg in self.free_regs if reg is not loc]
            return loc
        if v not in self.reg_bindings:
            prev_loc = self.stack_manager.loc(v)
            loc = self.force_allocate_reg(v, forbidden_vars)
            self.assembler.regalloc_mov(prev_loc, loc)
        assert v in self.reg_bindings
        if self.longevity[v][1] > self.position:
            # we need to find a new place for variable v and
            # store result in the same place
            loc = self.reg_bindings[v]
            del self.reg_bindings[v]
            if self.stack_manager.get(v) is None:
                self.move_variable_away(v, loc)
            self.reg_bindings[result_v] = loc
        else:
            self.reallocate_from_to(v, result_v)
            loc = self.reg_bindings[result_v]
        return loc

    # abstract methods, override

    def convert_to_imm(self, c):
        raise NotImplementedError("Abstract")
