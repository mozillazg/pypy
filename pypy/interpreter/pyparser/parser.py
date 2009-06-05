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

    def __init__(self, type, value, children):
        self.type = type
        self.value = value
        self.children = children


class Parser(object):

    def __init__(self, grammar):
        pass
