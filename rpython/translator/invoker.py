
import os
from twisted.internet import reactor
from twisted.protocols import basic
from twisted.internet import protocol, stdio
from twisted.internet.error import ProcessDone

class SubProcessProtocol(protocol.ProcessProtocol):
    def __init__(self, commander, name):
        self._commander = commander
        self._output = []
        self._name = name
        self._error = []

    def outReceived(self, out):
        self._output.append(out)

    def errReceived(self, err):
        self._error.append(err)

    def processExited(self, status):
        self._commander.process_exited()
        if status.value == ProcessDone:
            print repr((self._name, 0, "".join(self._output),
                        "".join(self._error)))
        else:
            print repr((self._name, status.value.exitCode,
                        "".join(self._output), "".join(self._error)))

MAX = 8

class Commander(basic.LineReceiver):
    delimiter = '\n'

    def __init__(self, max=MAX):
        self._counter = 0
        self._max = max
        self._queue = []

    def connectionMade(self):
        pass

    def process_exited(self):
        self._counter -= 1
        if self._queue:
            self._run(self._queue.pop())

    def _run(self, line):
        args = eval(line)
        reactor.spawnProcess(SubProcessProtocol(self, args[0]), args[1],
                             args[1:], env=os.environ.copy())
        self._counter += 1

    def lineReceived(self, line):
        if not line:
            reactor.stop()
            return
        assert line.startswith('(')
        if self._counter < self._max:
            self._run(line)
        else:
            self._queue.append(line)

stdio.StandardIO(Commander())
reactor.run()
