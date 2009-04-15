from pypy.conftest import gettestobjspace

class AppTestFork(object):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('thread', 'time'))
        cls.space = space

    def test_fork(self):
        # XXX This test depends on a multicore machine, as busy_thread must
        # aquire the GIL the instant that the main thread releases it.
        # It will incorrectly pass if the GIL is not grabbed in time.
        import thread
        import os
        import time
        
        def busy_thread():
            while True:
                time.sleep(0)

        thread.start_new(busy_thread, ())

        pid = os.fork()

        if pid == 0:
            os._exit(0)

        else:
            time.sleep(1)
            spid, status = os.waitpid(pid, os.WNOHANG)
            assert spid == pid
