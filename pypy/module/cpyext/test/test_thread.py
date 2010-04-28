
import thread, threading

from pypy.module.cpyext.test.test_api import BaseApiTest


class TestPyThread(BaseApiTest):
    def test_get_thread_ident(self, space, api):
        results = []
        def some_thread():
            w_res = api.PyThread_get_thread_ident(space)
            results.append((space.int_w(w_res), thread.get_ident()))

        some_thread()
        assert results[0][0] == results[0][1]

        th = threading.Thread(target=some_thread, args=())
        th.start()
        th.join()
        assert results[1][0] == results[1][1]
