import py
import tokenize
import token
import StringIO
from pypy.interpreter.pyparser.metaparser import ParserGenerator, PgenError
from pypy.interpreter.pyparser import parser


class MyGrammar(parser.Grammar):
    TOKENS = token.__dict__
    OPERATOR_MAP = {
        "+" : token.OP,
        "-" : token.OP,
        }
    KEYWORD_TOKEN = token.NAME


class TestParserGenerator:

    def gram_for(self, grammar_source):
        p = ParserGenerator(grammar_source + "\n")
        return p.build_grammar(MyGrammar)

    def test_multiple_rules(self):
        g = self.gram_for("foo: NAME bar\nbar: STRING")
        assert len(g.dfas) == 2
        assert g.start == g.symbol_ids["foo"]

    def test_simple(self):
        g = self.gram_for("eval: NAME\n")
        assert len(g.dfas) == 1
        eval_sym = g.symbol_ids["eval"]
        assert eval_sym in g.dfas
        assert g.start == eval_sym
        states, first = g.dfas[eval_sym]
        assert states == [[(0, 1)], [(0, 1)]]

    def test_items(self):
        g = self.gram_for("foo: NAME STRING OP '+'")
        assert len(g.dfas) == 1
        states = g.dfas[g.symbol_ids["foo"]][0]
        last = states[0][0][1]
        for state in states[1:-1]:
            assert last < state[0][1]
            last = state[0][1]

    def test_alternatives(self):
        g = self.gram_for("foo: STRING | OP")
        assert len(g.dfas) == 1

    def test_optional(self):
        g = self.gram_for("foo: [NAME]")

    def test_grouping(self):
        g = self.gram_for("foo: (NAME | STRING) OP")

    def test_keyword(self):
        g = self.gram_for("foo: 'some_keyword' 'for'")
        assert len(g.keyword_ids) == 2
        assert len(g.token_ids) == 0
        for keyword in ("some_keyword", "for"):
            label_index = g.keyword_ids[keyword]
            assert g.labels[label_index][1] == keyword

    def test_token(self):
        g = self.gram_for("foo: NAME")
        assert len(g.token_ids) == 1
        label_index = g.token_ids[token.NAME]
        assert g.labels[label_index][1] is None

    def test_operator(self):
        g = self.gram_for("add: NUMBER '+' NUMBER")
        assert len(g.keyword_ids) == 0
        assert len(g.token_ids) == 2
        assert g.labels[g.token_ids[token.OP]][1] is None

        exc = py.test.raises(PgenError, self.gram_for, "add: '/'").value
        assert str(exc) == "no such operator: '/'"

    def test_symbol(self):
        g = self.gram_for("foo: some_other_rule\nsome_other_rule: NAME")
        assert len(g.dfas) == 2
        assert len(g.labels) == 3

        exc = py.test.raises(PgenError, self.gram_for, "foo: no_rule").value
        assert str(exc) == "no such rule: 'no_rule'"

    def test_repeaters(self):
        g1 = self.gram_for("foo: NAME+")
        g2 = self.gram_for("foo: NAME*")
        assert g1.dfas != g2.dfas

        g = self.gram_for("foo: (NAME | STRING)*")

    def test_error(self):
        exc = py.test.raises(PgenError, self.gram_for, "hi").value
        assert str(exc) == "expected token OP but got NEWLINE"
        assert exc.location == ((1, 2), (1, 3), "hi\n")
        exc = py.test.raises(PgenError, self.gram_for, "hi+").value
        assert str(exc) == "expected ':' but got '+'"
        assert exc.location == ((1, 2), (1, 3), "hi+\n")

    def test_comments_and_whitespace(self):
        self.gram_for("\n\n# comment\nrule: NAME # comment")
