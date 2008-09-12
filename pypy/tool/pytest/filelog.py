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

    def write_log_entry(self, shortrepr, name, longrepr):
        print >>self.logfile, "%s %s" % (shortrepr, name)
        for line in longrepr.splitlines():
            print >>self.logfile, " %s" % line

    def log_outcome(self, ev):
        outcome = ev.outcome
        gpath = generic_path(ev.colitem)
        self.write_log_entry(outcome.shortrepr, gpath, str(outcome.longrepr))

    def log_event_to_file(self, ev):
        if isinstance(ev, event.ItemTestReport):
            self.log_outcome(ev)
        elif isinstance(ev, event.CollectionReport):
            if not ev.passed:
                self.log_outcome(ev)
        elif isinstance(ev, event.InternalException):
            path = ev.repr.reprcrash.path # fishing :(
            self.write_log_entry('!', path, str(ev.repr))
        


