from py.__.test.session import Session
from py.__.test import event


def generic_path(item):
    names = item.listnames()
    return '.'.join(names).replace('.(', '(')

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
            gpath = generic_path(ev.colitem)
            print >>self.logfile, "%s %s" % (outcome.shortrepr, gpath)

