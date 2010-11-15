import math
from pypy.rlib.rarithmetic import r_longlong
from pypy.rlib.objectmodel import we_are_translated

#
# Logic to decide which loops are old and not used any more.
#
# Idea: We use the notion of a global 'current generation' which
# is, in practice, the total number of loops and bridges produced
# so far.  When executing a loop:
#     (1) we set 'generation' to -1
#     (2) we execute it
#     (3) we set 'generation' to the latest generation
# (with a bit extra work to handle nested calls and to guarantee
# that 'generation' is always < 0 on a loop that is currently
# executing).
#
# A loop is said "old" if its generation is >= 0 but much smaller
# than the current generation.  If a loop L is old, and if all
# other loops from which we can reach L through
# 'contains_jumps_to' are also old, then we can free L.
#

class MemoryManager(object):

    def __init__(self, cpu):
        self.cpu = cpu
        self.check_frequency = -1
        # NB. use of r_longlong to be extremely far on the safe side:
        # this is increasing by one after each loop or bridge is
        # compiled, and it must not overflow.  If the backend implements
        # complete freeing in cpu.free_loop_and_bridges(), then it may
        # be possible to get arbitrary many of them just by waiting long
        # enough.  But in this day and age, you'd still never have the
        # patience of waiting for a slowly-increasing 64-bit number to
        # overflow :-)
        self.current_generation = r_longlong(0)
        self.next_check = r_longlong(-1)
        self.looptokens = []

    def set_max_age(self, max_age, check_frequency=0):
        if max_age <= 0:
            self.next_check = r_longlong(-1)
        else:
            self.max_age = max_age
            if check_frequency <= 0:
                check_frequency = int(math.sqrt(max_age))
            self.check_frequency = check_frequency
            self.next_check = self.current_generation + 1

    def next_generation(self):
        self.current_generation += 1
        if self.current_generation == self.next_check:
            self._free_old_loops_now()
            self.next_check = self.current_generation + self.check_frequency

    def enter_loop(self, looptoken):
        if not we_are_translated():
            assert looptoken in self.looptokens
            assert not looptoken.has_been_freed
        if looptoken.generation >= 0:
            looptoken.generation = -1
        else:
            looptoken.generation -= 1   # nested enter_loop()

    def leave_loop(self, looptoken):
        assert looptoken.generation < 0
        if looptoken.generation == -1:
            looptoken.generation = self.current_generation
        else:
            looptoken.generation += 1   # nested leave_loop()

    def record_loop(self, looptoken):
        looptoken.generation = self.current_generation
        self.looptokens.append(looptoken)

    def _free_old_loops_now(self):
        #
        # Initialize '_is_young' on all loop tokens
        max_generation = self.current_generation - self.max_age
        youngloops = []
        for looptoken in self.looptokens:
            if 0 <= looptoken.generation < max_generation:
                looptoken._is_young = False   # but may be turned to True later
            else:
                looptoken._is_young = True
                youngloops.append(looptoken)
        #
        # Propagate forward the knowledge of "is a young loop"
        while len(youngloops) > 0:
            looptoken = youngloops.pop()
            for jumptargettok in looptoken.contains_jumps_to:
                if not jumptargettok._is_young:
                    jumptargettok._is_young = True
                    youngloops.append(jumptargettok)
        #
        # Now free all looptokens that still have _is_young == False.
        i = 0
        while i < len(self.looptokens):
            looptoken = self.looptokens[i]
            if looptoken._is_young:
                i += 1
            else:
                self.looptokens[i] = self.looptokens[-1]
                del self.looptokens[-1]
                self.cpu.free_loop_and_bridges(looptoken)
