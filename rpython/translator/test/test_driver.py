import py

from rpython.translator.driver import TranslationDriver
import optparse


def test_c_no_jit():
    td = TranslationDriver()
    names = ['annotate', 'rtype', 'backendopt', 'source', 'compile']
    assert td.tasks == names


def test_c_with_jit():
    td = TranslationDriver({'jit': True})
    names = ['annotate', 'rtype', 'pyjitpl', 'backendopt', 'source', 'compile']
    assert td.tasks == names


def test_no_backendopt():
    td = TranslationDriver({'backendopt.none': True})
    names = ['annotate', 'rtype', 'source', 'compile']
    assert td.tasks == names
