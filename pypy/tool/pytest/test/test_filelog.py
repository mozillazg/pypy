import py

from pypy.tool.pytest import filelog
import os, StringIO

from py.__.test.collect import Node, Item
from py.__.test.event import ItemTestReport
from py.__.test.runner import OutcomeRepr


class Fake(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


def test_generic_path():
    p1 = Node('a', config='dummy')
    p2 = Node('B', parent=p1)
    p3 = Node('()', parent = p2)
    item = Item('c', parent = p3)

    res = filelog.generic_path(item)
    assert res == 'a.B().c'


def make_item(*names):
    node = None
    config = "dummy"
    for name in names[:-1]:
        node = Node(name, parent=node, config=config)
    return Item(names[-1], parent=node)

class TestFileLogSession(object):


    def test_sanity(self):
        option = Fake(eventlog=None)
        config = Fake(option=option)
        
        filelog.FileLogSession(config)

    def test_open_logfile(self):
        logfname = os.tempnam()
        
        option = Fake(eventlog=None, filelog=logfname)        
        config = Fake(option=option)
        
        sess = filelog.FileLogSession(config)

        assert len(sess.bus._subscribers) == 1

        assert sess.logfile
        assert os.path.exists(logfname)

        sess.logfile.close()
        os.unlink(logfname)

    def test_item_test_passed(self):            
        option = Fake(eventlog=None)
        config = Fake(option=option)
        sess = filelog.FileLogSession(config)
        sess.logfile = StringIO.StringIO()

        colitem = make_item('some', 'path', 'a', 'b')

        outcome=OutcomeRepr('execute', '.', '')
        rep_ev = ItemTestReport(colitem, outcome=outcome)

        sess.bus.notify(rep_ev)

        lines = sess.logfile.getvalue().splitlines()
        assert len(lines) == 1
        line = lines[0]
        assert line.startswith(". ")
        assert line[2:] == 'some.path.a.b'


    def test_item_test_skipped(self):
        py.test.skip("WIP: take the longrepr into account")
        option = Fake(eventlog=None)
        config = Fake(option=option)
        sess = filelog.FileLogSession(config)
        sess.logfile = StringIO.StringIO()
        outcome=OutcomeRepr('execute', 's', '')
        rep_ev = ItemTestReport(colitem, outcome=outcome)

        sess.bus.notify(rep_ev)

        lines = sess.logfile.getvalue().splitlines()
        assert len(lines) == 1
        line = lines[0]

        assert line.startswith("s ")
