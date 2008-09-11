from pypy.tool.pytest import filelog
import os, StringIO

from py.__.test.event import ItemTestReport


class Fake(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


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

    def test_item_test_passed_or_skipped(self):            
        option = Fake(eventlog=None)
        config = Fake(option=option)
        sess = filelog.FileLogSession(config)
        sess.logfile = StringIO.StringIO()

        colitem = Fake(repr_metainfo=lambda: Fake(fspath='some/path',
                                                  modpath="a.b"))
        outcome=Fake(shortrepr='.')
        rep_ev = ItemTestReport(colitem, outcome=outcome)

        sess.bus.notify(rep_ev)

        lines = sess.logfile.getvalue().splitlines()
        assert len(lines) == 1
        line = lines[0]
        assert line.startswith(". ")
        assert line[2:] == 'some/path:a.b'

        sess.logfile = StringIO.StringIO()
        colitem = Fake(repr_metainfo=lambda: Fake(fspath='some/path',
                                                  modpath=None))
        outcome=Fake(shortrepr='s')
        rep_ev = ItemTestReport(colitem, outcome=outcome)

        sess.bus.notify(rep_ev)

        lines = sess.logfile.getvalue().splitlines()
        assert len(lines) == 1
        line = lines[0]

        assert line.startswith("s ")
        assert line[2:] == 'some/path'        
        

# XXX integration tests
