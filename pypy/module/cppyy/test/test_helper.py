from pypy.module.cppyy import helper

def test_compound():
    assert helper.compound("int*") == "*"
    assert helper.compound("int* const *&") == "**&"
    assert helper.compound("std::vector<int>*") == "*"


def test_clean_type():
    assert helper.clean_type(" int***") == "int"
    assert helper.clean_type("std::vector<int>&") == "std::vector<int>"
