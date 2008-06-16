
class NFA(object):
    def __init__(self, num_states=0, transitions=None, final_states=None):
        self.num_states = 0
        self.transitions = {}
        self.final_states = {}

    def add_state(self, final=False):
        state = self.num_states
        self.num_states += 1
        if final:
            self.final_states[state] = None
        return self.num_states - 1

    def add_transition(self, state, input, next_state):
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
