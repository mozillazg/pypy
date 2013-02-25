import py

from rpython.translator.driver import TranslationDriver
import optparse


def test_c_no_jit():
    td = TranslationDriver()
    goals = ['annotate', 'rtype', 'backendopt', 'source', 'compile']
    assert td._tasks == goals


def test_c_with_jit():
    td = TranslationDriver({'jit': True})
    goals = ['annotate', 'rtype', 'pyjitpl', 'backendopt', 'source', 'compile']
    assert td._tasks == goals


def test_no_backendopt():
    td = TranslationDriver({'backendopt.none': True})
    goals = ['annotate', 'rtype', 'source', 'compile']
    assert td._tasks == goals
