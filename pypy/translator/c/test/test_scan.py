from pypy.translator.c.test import test_newgc


class TestScanMiniMarkGC(test_newgc.TestMiniMarkGC):
    gcpolicy = "minimark"
    gcrootfinder = "scan"
