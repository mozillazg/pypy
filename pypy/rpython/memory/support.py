from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.objectmodel import free_non_gc_object, we_are_translated
from pypy.rlib.rarithmetic import r_uint, LONG_BIT
from pypy.rlib.debug import ll_assert

DEFAULT_CHUNK_SIZE = 1019


def get_chunk_manager(chunk_size=DEFAULT_CHUNK_SIZE, cache={}):
    try:
        return cache[chunk_size]
    except KeyError:
        pass

    CHUNK = lltype.ForwardReference()
    CHUNK.become(lltype.Struct('AddressChunk',
                               ('next', lltype.Ptr(CHUNK)),
                               ('items', lltype.FixedSizeArray(
                                   llmemory.Address, chunk_size))))
    null_chunk = lltype.nullptr(CHUNK)

    class FreeList(object):
        _alloc_flavor_ = "raw"

        def __init__(self):
            self.free_list = null_chunk

        def get(self):
            if not self.free_list:
                # we zero-initialize the chunks to make the translation
                # backends happy, but we don't need to do it at run-time.
                zero = not we_are_translated()
                return lltype.malloc(CHUNK, flavor="raw", zero=zero)
                
            result = self.free_list
            self.free_list = result.next
            return result

        def put(self, chunk):
            if we_are_translated():
                chunk.next = self.free_list
                self.free_list = chunk
            else:
                # Don't cache the old chunks but free them immediately.
                # Helps debugging, and avoids that old chunks full of
                # addresses left behind by a test end up in genc...
                lltype.free(chunk, flavor="raw")

    unused_chunks = FreeList()
    cache[chunk_size] = unused_chunks, null_chunk
    return unused_chunks, null_chunk


def get_address_stack(chunk_size=DEFAULT_CHUNK_SIZE, cache={}):
    try:
        return cache[chunk_size]
    except KeyError:
        pass

    unused_chunks, null_chunk = get_chunk_manager(chunk_size)

    class AddressStack(object):
        _alloc_flavor_ = "raw"
        
        def __init__(self):
            self.chunk = unused_chunks.get()
            self.chunk.next = null_chunk
            self.used_in_last_chunk = 0
            # invariant: self.used_in_last_chunk == 0 if and only if
            # the AddressStack is empty

        def enlarge(self):
            new = unused_chunks.get()
            new.next = self.chunk
            self.chunk = new
            self.used_in_last_chunk = 0
        enlarge._dont_inline_ = True

        def shrink(self):
            old = self.chunk
            self.chunk = old.next
            unused_chunks.put(old)
            self.used_in_last_chunk = chunk_size
        shrink._dont_inline_ = True

        def append(self, addr):
            used = self.used_in_last_chunk
            if used == chunk_size:
                self.enlarge()
                used = 0
            self.chunk.items[used] = addr
            self.used_in_last_chunk = used + 1      # always > 0 here

        def non_empty(self):
            return self.used_in_last_chunk != 0

        def pop(self):
            used = self.used_in_last_chunk - 1
            ll_assert(used >= 0, "pop on empty AddressStack")
            result = self.chunk.items[used]
            self.used_in_last_chunk = used
            if used == 0 and self.chunk.next:
                self.shrink()
            return result

        def delete(self):
            cur = self.chunk
            while cur:
                next = cur.next
                unused_chunks.put(cur)
                cur = next
            free_non_gc_object(self)

        def foreach(self, callback, arg):
            """Invoke 'callback(address, arg)' for all addresses in the stack.
            Typically, 'callback' is a bound method and 'arg' can be None.
            """
            chunk = self.chunk
            count = self.used_in_last_chunk
            while chunk:
                while count > 0:
                    count -= 1
                    callback(chunk.items[count], arg)
                chunk = chunk.next
                count = chunk_size
        foreach._annspecialcase_ = 'specialize:arg(1)'

        def stack2dict(self):
            result = AddressDict()
            self.foreach(result.setitem, llmemory.NULL)
            return result

    cache[chunk_size] = AddressStack
    return AddressStack


def get_address_deque(chunk_size=DEFAULT_CHUNK_SIZE, cache={}):
    try:
        return cache[chunk_size]
    except KeyError:
        pass

    unused_chunks, null_chunk = get_chunk_manager(chunk_size)

    class AddressDeque(object):
        _alloc_flavor_ = "raw"
        
        def __init__(self):
            chunk = unused_chunks.get()
            chunk.next = null_chunk
            self.oldest_chunk = self.newest_chunk = chunk
            self.index_in_oldest = 0
            self.index_in_newest = 0

        def enlarge(self):
            new = unused_chunks.get()
            new.next = null_chunk
            self.newest_chunk.next = new
            self.newest_chunk = new
            self.index_in_newest = 0
        enlarge._dont_inline_ = True

        def shrink(self):
            old = self.oldest_chunk
            self.oldest_chunk = old.next
            unused_chunks.put(old)
            self.index_in_oldest = 0
        shrink._dont_inline_ = True

        def append(self, addr):
            index = self.index_in_newest
            if index == chunk_size:
                self.enlarge()
                index = 0
            self.newest_chunk.items[index] = addr
            self.index_in_newest = index + 1

        def non_empty(self):
            return (self.oldest_chunk != self.newest_chunk
                    or self.index_in_oldest < self.index_in_newest)

        def popleft(self):
            ll_assert(self.non_empty(), "pop on empty AddressDeque")
            index = self.index_in_oldest
            if index == chunk_size:
                self.shrink()
                index = 0
            result = self.oldest_chunk.items[index]
            self.index_in_oldest = index + 1
            return result

        def delete(self):
            cur = self.oldest_chunk
            while cur:
                next = cur.next
                unused_chunks.put(cur)
                cur = next
            free_non_gc_object(self)

    cache[chunk_size] = AddressDeque
    return AddressDeque


def AddressDict():
    if we_are_translated():
        return LLAddressDict()
    else:
        return BasicAddressDict()

class BasicAddressDict(object):
    def __init__(self):
        self.data = {}
    def _key(self, addr):
        return addr._fixup().ptr._obj
    def delete(self):
        pass
    def contains(self, keyaddr):
        return self._key(keyaddr) in self.data
    def get(self, keyaddr, default=llmemory.NULL):
        return self.data.get(self._key(keyaddr), default)
    def setitem(self, keyaddr, valueaddr):
        assert keyaddr
        self.data[self._key(keyaddr)] = valueaddr
    def add(self, keyaddr):
        self.setitem(keyaddr, llmemory.NULL)

# if diff_bit == -1, the node is a key/value pair (key=left/value=right)
# if diff_bit >= 0, then the node is the root of a subtree where:
#   * the keys have all exactly the same bits > diff_bit
#   * the keys whose 'diff_bit' is 0 are in the 'left' subtree
#   * the keys whose 'diff_bit' is 1 are in the 'right' subtree
ADDRDICTNODE = lltype.Struct('AddrDictNode',
                             ('diff_bit', lltype.Signed),
                             ('left', llmemory.Address),
                             ('right', llmemory.Address))

class LLAddressDict(object):
    _alloc_flavor_ = "raw"

    def __init__(self):
        self.root = lltype.malloc(ADDRDICTNODE, flavor='raw')
        self.root.diff_bit = -1
        self.root.left = llmemory.NULL

    def delete(self):
        node = self.root
        parent = lltype.nullptr(ADDRDICTNODE)
        while True:
            if node.diff_bit >= 0:
                next = _node_reveal(node.left)
                node.left = _node_hide(parent)
                parent = node
                node = next
            else:
                lltype.free(node, flavor='raw')
                if not parent:
                    break
                node = _node_reveal(parent.right)
                grandparent = _node_reveal(parent.left)
                lltype.free(parent, flavor='raw')
                parent = grandparent
        free_non_gc_object(self)

    def contains(self, keyaddr):
        if keyaddr:
            node = self._lookup(keyaddr)
            return keyaddr == node.left
        else:
            return False

    def get(self, keyaddr, default=llmemory.NULL):
        if keyaddr:
            node = self._lookup(keyaddr)
            if keyaddr == node.left:
                return node.right
        return default

    def setitem(self, keyaddr, valueaddr):
        ll_assert(bool(keyaddr), "cannot store NULL in an AddressDict")
        node = self._lookup(keyaddr)
        if node.left == llmemory.NULL or node.left == keyaddr:
            node.left = keyaddr
            node.right = valueaddr
        else:
            number1 = r_uint(llmemory.cast_adr_to_int(keyaddr))
            number2 = r_uint(llmemory.cast_adr_to_int(node.left))
            diff = number1 ^ number2
            parentnode = self._lookup(keyaddr, difflimit = diff >> 1)
            # all subnodes of parentnode have a key that is equal to
            # 'keyaddr' for all bits in range(0, msb(diff)), and differs
            # from 'keyaddr' exactly at bit msb(diff).
            # At this point, parentnode.diff_bit < msb(diff).
            nextbit = parentnode.diff_bit
            copynode = lltype.malloc(ADDRDICTNODE, flavor='raw')
            copynode.diff_bit = nextbit
            copynode.left = parentnode.left
            copynode.right = parentnode.right
            bit = self._msb(diff, nextbit + 1)
            newnode = lltype.malloc(ADDRDICTNODE, flavor='raw')
            parentnode.diff_bit = bit
            ll_assert(number1 & (r_uint(1) << bit) !=
                      number2 & (r_uint(1) << bit), "setitem: bad 'bit'")
            if number1 & (r_uint(1) << bit):
                parentnode.left = _node_hide(copynode)
                parentnode.right = _node_hide(newnode)
            else:
                parentnode.left = _node_hide(newnode)
                parentnode.right = _node_hide(copynode)
            newnode.diff_bit = -1
            newnode.left = keyaddr
            newnode.right = valueaddr
        if not we_are_translated():
            assert self.contains(keyaddr)

    def add(self, keyaddr):
        self.setitem(keyaddr, llmemory.NULL)

    def _msb(self, value, lowerbound=0):
        # Most Significant Bit: '(1<<result)' is the highest bit set in 'value'
        ll_assert(value >= (r_uint(1) << lowerbound),
                  "msb: bad value or lowerbound")
        if value >= (r_uint(1) << (LONG_BIT-1)):
            return LONG_BIT-1    # most significant possible bit
        bit = lowerbound
        while (value >> bit) > r_uint(1):
            bit += 1
        return bit

    def _lookup(self, addr, difflimit=r_uint(0)):
        # * with difflimit == 0, find and return the leaf node whose key is
        #   equal to or closest from 'addr'.
        # * with difflimit > 0, look for the node N closest to the root such
        #   that all the keys of the subtree starting at node N are equal to
        #   the given 'addr' at least for all bits > msb(difflimit).
        number = r_uint(llmemory.cast_adr_to_int(addr))
        node = self.root
        while node.diff_bit >= 0:
            mask = r_uint(1) << node.diff_bit
            if mask <= difflimit:
                return node
            if number & mask:
                node = _node_reveal(node.right)
            else:
                node = _node_reveal(node.left)
        return node

_node_hide = llmemory.cast_ptr_to_adr

def _node_reveal(nodeaddr):
    return llmemory.cast_adr_to_ptr(nodeaddr, lltype.Ptr(ADDRDICTNODE))
