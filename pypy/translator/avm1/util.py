
import struct, os, math

ALIGN_LEFT = "left"
ALIGN_RIGHT = "right"

def serialize_u32(value):
    s = ""
    while True:
        bits = value & 0b01111111 # low 7 bits
        value >>= 7
        if not value:
            s += chr(bits)
            break
        s += chr(0b10000000 | bits)
    return s

class BitStream(object):

    """ BitStream is a class for taking care of data structures that are bit-packed, like SWF."""
    
    def __init__(self, bits=[]):
        """
        Constructor.
        """
        self.bits = [bool(b) and b != "0" for b in bits]
        self.cursor = 0
        self.chunks = set((0,))

    def read_bit(self):
        """Reads a bit from the bit stream and returns it as either True or False. IndexError is thrown if reading past the end of the stream."""
        self.cursor += 1
        return self.bits[self.cursor-1]
    
    def read_bits(self, length):
        """Reads length bits and return them in their own bit stream."""
        self.cursor += length
        return BitStream(self.bits[self.cursor-length:self.cursor])
    
    def write_bit(self, value):
        """Writes the boolean value to the bit stream."""
        if self.cursor < len(self.bits):
            self.bits[self.cursor] = bool(value)
        else:
            self.bits.append(bool(value))
        self.cursor += 1

    def write_bits(self, bits, offset=0, length=0):
        """Writes length bits from bits to this bit stream, starting reading at offset. If length
        is 0, the entire stream is used."""
        if length < 1:
            length = len(bits)

        if length > self.bits_available():
            for i in range(length - self.bits_available()):
                self.bits.append(False)
        
        self.bits[self.cursor:self.cursor+length] = (bool(x) for x in bits[offset:offset+length])
        self.cursor += length

    def read_int_value(self, length):
        """Read length bits and return a number containing those bits with the last bit read being
        the least significant bit."""
        n = 0
        for i in reversed(xrange(length)):
            n |= self.read_bit() << i
        return n
    
    def write_int_value(self, value, length=-1):
        """Writes an int to the specified number of bits in the stream, the most significant bit
        first. If length is not specified or negative, the log base 2 of value is taken."""
        
        if length < 0:
            try:
                length = int(math.ceil(math.log(value, 2))) # Get the log base 2, or number of bits value will fit in.
            except ValueError:
                length = 1
        self.chunk()
        for i in reversed(xrange(length)):
            self.write_bit(value & (1 << i))
            
    
    def read_fixed_value(self, eight_bit):
        """Reads a fixed point number, either 8.8 or 16.16. If eight_bit is True, an
        8.8 format is used, otherwise 16.16."""
        return self.read_int_value(length) / float(0x100 if eight_bit else 0x10000)

    def write_fixed_value(self, value, eight_bit):
        """Writes a fixed point number of length, decimal part first. If eight_bit is True,
        an 8.8 format is used instead of a 16.16 format."""
        self.write_bit_value(value * float(0x100 if eight_bit else 0x10000), 8 if eight_bit else 16)

    # Precalculated, see the Wikipedia links below.
    _EXPN_BIAS = {16: 16, 32: 127, 64: 1023}
    _N_EXPN_BITS = {16: 5, 32: 8, 64: 8}
    _N_FRAC_BITS = {16: 10, 32: 23, 64: 52}
    _FLOAT_NAME = {16: "float16", 32: "float", 64: "double"}

    def read_float_value(self, length):
        """Reads a floating point number of length, which must be 16 (float16), 32 (float),
        or 64 (double). See: http://en.wikipedia.org/wiki/IEEE_floating-point_standard"""

        if length not in BitStream._FLOAT_NAME:
            raise ValueError, "length is not 16, 32 or 64."
        
        sign = self.read_bit()
        expn = self.read_int_value(BitStream._N_EXPN_BITS[length])
        frac = self.read_int_value(BitStream._N_FRAC_BITS[length])
        
        frac_total = float(1 << BitStream._N_FRAC_BITS[length])

        if expn == 0:
            if frac == 0:
                return 0
            else:
                return ~frac + 1 if sign else frac
        elif expn == frac_total - 1:
            if frac == 0:
                return float("-inf") if sign else float("inf")
            else:
                return float("nan")

        return (-1 if sign else 1) * 2**(expn - BitStream._EXPN_BIAS[length]) * (1 + frac / frac_total)

    def write_float_value(self, value, length):
        """Writes a floating point number of length, which must be 16 (float16),
        32 (float), or 64 (double). See: http://en.wikipedia.org/wiki/IEEE_floating-point_standard"""
        
        if length not in BitStream._FLOAT_NAME:
            raise ValueError, "length is not 16, 32 or 64."
        
        if value == 0: # value is zero, so we don't care about length
            self.write_int_value(0, length)
        
        if math.isnan(value):
            self.one_fill(length)
            return
        elif value == float("-inf"): # negative infinity
            self.one_fill(BitStream._N_EXPN_BITS[length] + 1) # sign merged
            self.zero_fill(BitStream._N_FRAC_BITS[length])
            return
        elif value == float("inf"): # positive infinity
            self.write_bit(False)
            self.one_fill(BitStream._N_EXPN_BITS[length])
            self.zero_fill(BitStream._N_FRAC_BITS[length])
            return

        if value < 0:
            self.write_bit(True)
            value = ~value + 1
        else:
            self.write_bit(False)
        
        exp = BitStream._EXPN_BIAS[length]
        if value < 1:
            while int(value) != 1:
                value *= 2
                exp -= 1
        else:
            while int(value) != 1:
                value /= 2
                exp += 1

        if exp < 0 or exp > ( 1 << BitStream._N_EXPN_BITS[length] ):
            raise ValueError, "Exponent out of range in %s [%d]." % (BitStream._FLOAT_NAME[length], length)

        frac_total = 1 << BitStream._N_FRAC_BITS[length]
        self.write_int_value(exp, BitStream._N_EXPN_BITS[length])
        self.write_int_value(int((value-1)*frac_total) & (frac_total - 1), BitStream._N_FRAC_BITS[length])

    
    def one_fill(self, amount):
        """Fills amount bits with one. The equivalent of calling
        self.write_boolean(True) amount times, but more efficient."""

        if amount > self.bits_available():
            for i in range(amount - self.bits_available()):
                self.bits.append(True)
        
        self.bits[self.cursor:self.cursor+amount] = [True] * amount
        self.cursor += amount
        
    def zero_fill(self, amount):
        """Fills amount bits with zero. The equivalent of calling
        self.write_boolean(False) amount times, but more efficient."""

        if amount > self.bits_available():
            for i in range(amount - self.bits_available()):
                self.bits.append(False)
        
        self.bits[self.cursor:self.cursor+amount] = [False] * amount
        self.cursor += amount
        
    def seek(self, offset, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            self.cursor = offset
        elif whence == os.SEEK_CUR:
            self.cursor += offset
        elif whence == os.SEEK_END:
            self.cursor = len(self.bits) - abs(offset)

    def rewind(self):
        self.seek(0, os.SEEK_SET)
        
    def skip_to_end(self):
        self.seek(0, os.SEEK_END)

    def bits_available(self):
        return len(self.bits) - self.cursor

    def flush(self):
        self.zero_fill(8 - (len(self) % 8))

    def chunk(self):
        self.chunks.add(int(math.ceil(self.cursor / 8.)))
    
    def __len__(self):
        return len(self.bits)

    def __getitem__(self, i):
        return self.bits.__getitem__(i)

    def __setitem__(self, i, v):
        return self.bits.__setitem__(i, v)
    
    def __str__(self):
        return "".join("1" if b else "0" for b in self.bits)

    def __add__(self, bits):
        b = BitStream()
        b.write_bits(self)
        b.write_bits(bits)
        return b

    def __iadd__(self, bits):
        self.write_bits(bits)
        return self
    
    def serialize(self, align=ALIGN_LEFT, endianness=None):
        """Serialize bit array into a byte string, aligning either
        on the right (ALIGN_RIGHT) or left (ALIGN_LEFT). Endianness
        can also be "<" for little-endian modes."""
        lst = self.bits[:]
        leftover = len(lst) % 8
        if leftover > 0:
            if align == ALIGN_RIGHT:
                lst[:0] = [False] * (8-leftover) # Insert some False values to pad the list so it is aligned to the right.
            else:
                lst += [False] * (8-leftover)
        
        lst = BitStream(lst)
        tmp = [lst.read_int_value(8) for i in xrange(int(math.ceil(len(lst)/8.0)))]
        
        bytes = [None] * len(tmp)
        if endianness == "<":
            m = sorted(self.chunks) + [len(tmp)]
            for start, end in zip(m, m[1::]):
                bytes[start:end] = tmp[end-1:None if start == 0 else start-1:-1]
        else:
            bytes = tmp
        return ''.join(chr(b) for b in bytes)

    def parse(self, string, endianness="<"):
        """Parse a bit array from a byte string into this BitStream."""
        for char in string:
            self.write_int_value(ord(char), 8)
    
