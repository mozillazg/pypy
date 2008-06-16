
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

class Builder(object):
    def __init__(self):
        self.nfa = NFA()
        self.current_state = self.nfa.add_state()

    def add_transition(self, c, state=-1, final=False):
        if state == -1:
            state = self.nfa.add_state(final)
        elif final:
            self.nfa.final_states[state] = None
        self.nfa.add_transition(self.current_state, c, state)
        self.current_state = state

    def add_cycle(self, state):
        """ We change all transitions pointing to current state
        to point to state passed as argument
        """
        to_replace = self.current_state
        for (fr, ch), v in self.nfa.transitions.items():
            for i in range(len(v)):
                if v[i] == to_replace:
                    v[i] = state
            if fr == to_replace:
                del self.nfa.transitions[(fr, ch)]
            self.nfa.transitions[(state, ch)] = v
        try:
            del self.nfa.final_states[to_replace]
        except KeyError:
            pass
        else:
            self.nfa.final_states[state] = None

def no_more_chars(i, input):
    for k in range(i+1, len(input)):
        if input[k] >= 'a' and input[k] <= 'z':
            return False
    return True

def compile_regex(input):
    """ Simple compilation routine, just in order to not have to mess
    up with creating automaton by hand. We assume alphabet to be a-z
    """
    builder = Builder()
    i = 0
    last_anchor = builder.current_state
    joint_point = -1
    paren_stack = []
    last_state = -1
    while i < len(input):
        c = input[i]
        if c >= 'a' and c <= 'z':
            final = no_more_chars(i, input)
            last_state = builder.current_state
            if (final or input[i + 1] == ')') and joint_point != -1:
                builder.add_transition(c, state=joint_point, final=final)
                join_point = -1
            else:
                builder.add_transition(c, final=final)
        elif c == "|":
            last_state = -1
            joint_point = builder.current_state
            builder.current_state = last_anchor
        elif c == '(':
            paren_stack.append((builder.current_state, last_anchor, joint_point))
            last_anchor = builder.current_state
            joint_point = -1
        elif c == ')':
            if not paren_stack:
                raise ValueError("Unmatched parentheses")
            last_state, last_anchor, joint_point = paren_stack.pop()
        elif c == '*':
            if last_state == -1:
                raise ValueError("Mismatched *")
            builder.add_cycle(last_state)
        else:
            raise ValueError("Unknown char %s" % c)
        i += 1
    return builder.nfa
