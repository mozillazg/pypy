

from pypy.translator.avm.util import BitStream, ALIGN_RIGHT, ALIGN_LEFT

def test_write_bit():
    bits = BitStream()
    bits.write_bit(True)
    bits.write_bit(0)
    bits.write_bit(1)
    assert str(bits) == "101"

def test_read_bit():
    bits = BitStream("101")
    assert bits.read_bit() == True
    assert bits.read_bit() == False
    assert bits.read_bit() == True

def test_write_bits():
    bits = BitStream()
    bits.write_bits([1,1,0,1], 0, 3) # Length of 3! Stop after 3 bits, 110
    bits.write_bits([1,1,0,1], 2, 2) # Write the last two bits, 01
    assert str(bits) == "11001"

def test_read_bits():
    bits = BitStream("01101")
    assert str(bits.read_bits(4))

def test_write_int_value():
    bits = BitStream()
    bits.write_int_value(51, 6)
    assert str(bits) == "110011"

def test_read_int_value():
    bits = BitStream("101010")
    assert bits.read_int_value(6) == 42

def test_write_fixed_value():
    bits = BitStream()
    bits.write_fixed_value(1.5)
    assert str(bits) == "11000000000000000"
    bits.rewind()
    bits.write_fixed_value(6.2, 20)
    assert str(bits) == "01100011001100110011"

def test_read_fixed_value():
    bits = BitStream("01100011001100110011") # 6.2
    val = bits.read_fixed_value(20)
    assert abs(6.2 - val) < 0.1

def test_write_float_value():
    bits = BitStream()
    bits.write_float_value(0.15625, 32)
    assert str(bits) == "00111110001000000000000000000000"
    # 00111110001000000000000000000000 = 0.15625

def test_read_float_value():
    bits = BitStream("00111110001000000000000000000000")
    val = bits.read_float_value(32)
    assert val == 0.15625

def test_serialize():
    bits = BitStream("101010")
    assert bits.serialize(ALIGN_RIGHT) == "\x2A" # 00101010 =  42 = 0x2A
    assert bits.serialize(ALIGN_LEFT) == "\xA8"  # 10101000 = 168 = 0xA8
    bits = BitStream("1100110011")
    assert bits.serialize(ALIGN_RIGHT) == "\x03\x33" # 1100110011 = 00000011 00110011 =  03  51 = 03 33
    assert bits.serialize(ALIGN_LEFT) == "\xCC\xC0"  # 1100110011 = 11001100 11000000 = 204 192 = CC C0
