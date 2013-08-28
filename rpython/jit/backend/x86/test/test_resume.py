
from rpython.jit.backend.x86.test.test_basic import Jit386Mixin
from rpython.jit.backend.llsupport.test.test_resume import ResumeTest

class TestResumeX86(Jit386Mixin, ResumeTest):
    # for the individual tests see
    # ====> ../../llsupport/test/test_resume.py
    pass
