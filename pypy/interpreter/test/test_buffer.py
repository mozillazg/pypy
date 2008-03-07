import py
from pypy.interpreter.buffer import Buffer


class TestBuffer:

    def test_buffer_w(self):
        space = self.space
        w_hello = space.wrap('hello world')
        buf = space.buffer_w(w_hello)
        assert isinstance(buf, Buffer)
        assert buf.len == 11
        assert buf.as_str() == 'hello world'
        assert buf.getslice(1, 6) == 'ello '
        space.raises_w(space.w_TypeError, space.buffer_w, space.wrap(5))
        space.raises_w(space.w_TypeError, space.buffer, space.wrap(5))
