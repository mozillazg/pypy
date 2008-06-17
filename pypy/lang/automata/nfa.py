
class NFA(object):
    def __init__(self, num_states=0, transitions=None, final_states=None):
        self.num_states = 0
        self.transitions = {}
        self.final_states = {}
        self.has_epsilon_moves = False

    def add_state(self, final=False):
        state = self.num_states
        self.num_states += 1
        if final:
            self.final_states[state] = None
        return self.num_states - 1

    def add_transition(self, state, input, next_state):
        if input == '?':
            self.has_epsilon_moves = True
        if (state, input) in self.transitions:
            self.transitions[state, input].append(next_state)
        else:
            self.transitions[state, input] = [next_state]

    def get_transitions(self, state, input):
        return self.transitions[state, input]

    def get_language(self):
        all_chars = {}
        for state, input in self.transitions:
            all_chars[input] = None
        return all_chars

    def _remove_identical_states(self):
        """ Identical states are ones that have similiar e-moves
        forward, merge them
        """
        possible_merges = {}
        prohibited_merges = {}
        changed = False
        for (s, v), next_s_l in self.transitions.items():
            if v == '?':
                for next_s in next_s_l:
                    if next_s in possible_merges:
                        possible_merges[next_s][s] = None
                    else:
                        possible_merges[next_s] = {s:None}
            else:
                prohibited_merges[s] = None
        for k, v in possible_merges.items():
            v = dict.fromkeys([i for i in v if i not in prohibited_merges])
            if len(v) > 1:
                first = v.keys()[0]
                self.merge_states(first, v)
                changed = True
        return changed

    def merge_states(self, to_what, vdict):
        for (s, v), next_s_l in self.transitions.items():
            for i in range(len(next_s_l)):
                next = next_s_l[i]
                if next in vdict:
                    next_s_l[i] = to_what
        for k in self.final_states.keys():
            if k in vdict:
                self.final_states[to_what] = None
                del final_states[k]

    def _remove_epsilon_moves(self):
        for (s, v), next_s_l in self.transitions.items():
            if v == '?': # epsilon move
                for next_s in next_s_l:
                    self.merge_moves(next_s, s)
                    if next_s in self.final_states:
                        self.final_states[s] = None
                del self.transitions[(s, v)]
                return False
        return True

    def remove_epsilon_moves(self):
        if not self.has_epsilon_moves:
            return
        changed = True
        while changed:
            changed = self._remove_identical_states()
            self.cleanup()
        changed = False
        while not changed:
            changed = self._remove_epsilon_moves()
        self.cleanup()
        self.has_epsilon_moves = False

    def _cleanup(self):
        all = {0:None}
        accessible = {0:None}
        for (s, v), next_s_l in self.transitions.items():
            all[s] = None
            for next in next_s_l:
                accessible[next] = None
                all[next] = None
        for fs in self.final_states:
            all[fs] = None
        if all == accessible:
            return False
        else:
            for (s, v), next_s_l in self.transitions.items():
                if s not in accessible:
                    del self.transitions[(s, v)]
            for fs in self.final_states.keys():
                if fs not in accessible:
                    del self.final_states[fs]
            return True

    def cleanup(self):
        while self._cleanup():
            pass

    def merge_moves(self, to_replace, replacement):
        for (s, c), targets in self.transitions.items():
            if s == to_replace:
                for target in targets:
                    self.add_transition(replacement, c, target)
    
    def __repr__(self):
        from pprint import pformat
        return "NFA%s" % (pformat(
            (self.num_states, self.transitions, self.final_states)))

def getautomaton():
    a = NFA()
    s0 = a.add_state()
    s1 = a.add_state()
    s2 = a.add_state(final=True)
    a.add_transition(s0, "a", s0)
    a.add_transition(s0, "c", s1) 
    a.add_transition(s0, "c", s0)
    a.add_transition(s0, "b", s2) 
    a.add_transition(s1, "b", s2)
    return a

def recognize(automaton, s):
    " a simple recognizer"
    state = 0
    stack = []
    i = 0
    automaton.remove_epsilon_moves()
    while True:
        char = s[i]
        try:
            states = automaton.get_transitions(state, char)
        except KeyError:
            if len(stack) == 0:
                return False
            i, state = stack.pop()
        else:
            if len(states) == 1:
                i += 1
                state = states[0]
            else:
                for next_state in states[1:]:
                    stack.append((i + 1, next_state))
                i += 1
                state = states[0]
        while i == len(s):
            if state in automaton.final_states:
                return True
            if len(stack) == 0:
                return False
            i, state = stack.pop()

    return state in automaton.final_states

def in_alphabet(c):
    return c >= 'a' and c <= 'z'

def compile_part(nfa, start_state, input, pos):
    i = pos
    last_state = -1
    state = start_state
    while i < len(input):
        c = input[i]
        if in_alphabet(c):
            next_state = nfa.add_state()
            nfa.add_transition(state, c, next_state)
            state = next_state
        elif c == ')':
            break
        elif c == '(':
            i, state = compile_part(nfa, state, input, i + 1)
        elif c == '|':
            if last_state == -1:
                last_state = nfa.add_state()
            nfa.add_transition(state, '?', last_state)
            state = start_state
        elif c == '*':
            nfa.add_transition(state, '?', start_state)
            state = start_state
        else:
            raise ValueError("Unknown char %s" % c)
        i += 1
    if last_state != -1:
        nfa.add_transition(state, '?', last_state)
        state = last_state
    return i, state

def compile_regex(input):
    start = 0
    nfa = NFA()
    start_state = nfa.add_state()
    pos, state = compile_part(nfa, start_state, input, 0)
    if pos != len(input):
        raise ValueError("Mismatched parenthesis")
    nfa.final_states[state] = None
    return nfa
