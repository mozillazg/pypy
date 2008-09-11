from py.__.test.session import Session
from py.__.test import event

class FileLogSession(Session):

    def __init__(self, config):
        super(FileLogSession, self).__init__(config)
        self.bus.subscribe(self.log_event_to_file)
        if hasattr(config.option, 'filelog'):
            filelog = config.option.filelog
            self.logfile = open(filelog, 'w') # line buffering ?


    def log_event_to_file(self, ev):
        if isinstance(ev, event.ItemTestReport):
            outcome = ev.outcome
            metainfo = ev.colitem.repr_metainfo()
            path = metainfo.fspath
            modpath = metainfo.modpath
            if modpath:
                path += ":%s" % modpath
            print >>self.logfile, "%s %s" % (outcome.shortrepr, path)

