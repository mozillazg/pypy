from pypy.module.cppyy import helper

def test_compound():
    assert helper.compound("int*") == ("*", None)
    assert helper.compound("int* const *&") == ("**&", None)
    assert helper.compound("std::vector<int>*") == ("*", None)
    assert helper.compound("unsigned long int[5]") == ("[]", 5)


def test_clean_type():
    assert helper.clean_type(" int***") == "int"
    assert helper.clean_type("std::vector<int>&") == "std::vector<int>"
    assert helper.clean_type("unsigned short int[3]") == "unsigned short int"
