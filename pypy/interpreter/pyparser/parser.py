"""
A CPython inspired RPython parser.
"""


class Grammar(object):
    """
    Base Grammar object.

    Pass this to ParserGenerator.build_grammar to fill it with useful values for
    the Parser.
    """

    def __init__(self):
        self.symbol_ids = {}
        self.symbol_names = {}
        self.symbol_to_label = {}
        self.keyword_ids = {}
        self.dfas = {}
        self.labels = []
        self.token_ids = {}

    def _freeze_(self):
        # Remove some attributes not used in parsing.
        del self.symbol_to_label
        del self.symbol_names
        del self.symbol_ids
        return True


class Node(object):

    __slots__ = "type value children lineno column".split()

    def __init__(self, type, value, children, lineno, column):
        self.type = type
        self.value = value
        self.children = children
        self.lineno = lineno
        self.column = column

    def __eq__(self, other):
        # For tests.
        return (self.type == other.type and
                self.value == other.value and
                self.children == other.children)

    def __repr__(self):
        if self.value is None:
            return "Node(type=%s, children=%r)" % (self.type, self.children)
        else:
            return "Node(type=%s, value=%r)" % (self.type, self.value)


class ParseError(Exception):

    def __init__(self, msg, token_type, value, lineno, column):
        Exception.__init__(self, msg)
        self.token_type = token_type
        self.value = value
        self.lineno = lineno
        self.column = column

    def __str__(self):
        return "ParserError(%s, %r)" % (self.token_type, self.value)


class Parser(object):

    def __init__(self, grammar):
        self.grammar = grammar

    def prepare(self, start=-1):
        if start == -1:
            start = self.grammar.start
        self.root = None
        current_node = Node(start, None, [], 0, 0)
        self.stack = []
        self.stack.append((self.grammar.dfas[start], 0, current_node))

    def add_token(self, token_type, value, lineno, column):
        label_index = self.classify(token_type, value, lineno, column)
        while True:
            dfa, state_index, node = self.stack[-1]
            states, first = dfa
            arcs = states[state_index]
            for i, next_state in arcs:
                sym_id = self.grammar.labels[i]
                if label_index == i:
                    self.shift(next_state, token_type, value, lineno, column)
                    state_index = next_state
                    while states[state_index] == [(0, state_index)]:
                        self.pop()
                        if not self.stack:
                            return True
                        dfa, state_index, node = self.stack[-1]
                        states = dfa[0]
                    return False
                elif sym_id >= 256:
                    sub_node_dfa = self.grammar.dfas[sym_id]
                    if label_index in sub_node_dfa[1]:
                        self.push(sub_node_dfa, next_state, sym_id, lineno,
                                  column)
                        break
            else:
                if (0, state_index) in arcs:
                    self.pop()
                    if not self.stack:
                        raise ParseError("too much input", token_type, value,
                                         lineno, column)
                else:
                    raise ParseError("bad input", token_type, value, lineno,
                                     column)

    def classify(self, token_type, value, lineno, column):
        if token_type == self.grammar.KEYWORD_TOKEN:
            label_index = self.grammar.keyword_ids.get(value, -1)
            if label_index != -1:
                return label_index
        label_index = self.grammar.token_ids.get(token_type, -1)
        if label_index == -1:
            raise ParseError("invalid token", token_type, value, lineno, column)
        return label_index

    def shift(self, next_state, token_type, value, lineno, column):
        dfa, state, node = self.stack[-1]
        new_node = Node(token_type, value, None, lineno, column)
        node.children.append(new_node)
        self.stack[-1] = (dfa, next_state, node)

    def push(self, next_dfa, next_state, node_type, lineno, column):
        dfa, state, node = self.stack[-1]
        new_node = Node(node_type, None, [], lineno, column)
        self.stack[-1] = (dfa, next_state, node)
        self.stack.append((next_dfa, 0, new_node))

    def pop(self):
        dfa, state, node = self.stack.pop()
        if self.stack:
            self.stack[-1][2].children.append(node)
        else:
            self.root = node
