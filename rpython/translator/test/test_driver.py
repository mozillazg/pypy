import py

from rpython.translator.driver import TranslationDriver
import optparse


def test_c_no_jit():
    td = TranslationDriver()
    names = ['annotate', 'rtype', 'backendopt', 'database', 'source',
             'compile']
    assert [task.task_name for task in td.tasks] == names


def test_c_with_jit():
    td = TranslationDriver({'jit': True})
    names = ['annotate', 'rtype', 'pyjitpl', 'backendopt', 'database',
             'source', 'compile']
    assert [task.task_name for task in td.tasks] == names


def test_no_backendopt():
    td = TranslationDriver({'backendopt.none': True})
    names = ['annotate', 'rtype', 'database', 'source', 'compile']
    assert [task.task_name for task in td.tasks] == names
