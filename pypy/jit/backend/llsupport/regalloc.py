
from pypy.jit.metainterp.history import Const
from pypy.rlib.objectmodel import we_are_translated

class StackManager(object):
    """ Manage stack positions
    """

class RegisterManager(object):
    """ Class that keeps track of register allocations
    """
    def __init__(self, register_pool, longevity, no_lower_byte_regs=()):
        self.free_regs = register_pool[:]
        self.all_regs = register_pool
        self.longevity = longevity
        self.reg_bindings = {}
        self.position = 0
        self.no_lower_byte_regs = no_lower_byte_regs

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
            if res:
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

