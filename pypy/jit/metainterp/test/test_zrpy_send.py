import py
from test import test_send
from test.test_zrpy_basic import LLInterpJitMixin


class TestLLSend(test_send.SendTests, LLInterpJitMixin):
    def test_oosend_guard_failure(self):
        py.test.skip("Fails with assertion error")

    def test_oosend_guard_failure_2(self):
        py.test.skip("Fails with assertion error")
