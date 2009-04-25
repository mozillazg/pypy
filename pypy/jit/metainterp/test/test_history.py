import py

from pypy.rlib import objectmodel
from pypy.translator.translator import TranslationContext
from pypy.jit.backend.llgraph.runner import LLtypeCPU
from pypy.jit.metainterp import codewriter, history

def check_roundtrip(v):
    bytecode = codewriter.assemble_constant_code(v.serialize())
    decoder = codewriter.JitCodeDecoder(bytecode)
    const_type = decoder.load_int()
    cpu = LLtypeCPU(TranslationContext())
    result = history.unserialize_prebuilt(const_type, decoder, cpu)
    assert result == v

def test_serialize_const_int():
    check_roundtrip(history.ConstInt(4))

    sym = history.ConstInt(objectmodel.CDefinedIntSymbolic(4))
    py.test.raises(history.Unserializable, sym.serialize)
