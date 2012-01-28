from pypy.translator.c.test import test_newgc


class TestMiniMarkGC(test_newgc.TestMiniMarkGC):
    gcrootfinder = "scan"
