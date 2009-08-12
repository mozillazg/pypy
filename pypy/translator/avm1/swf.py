
import struct

from pypy.translator.avm.util import BitStream
from pypy.translator.avm.records import Rect

class SwfData(object):

    def __init__(self, width=600, height=400, fps=24, compress=False, version=10):
        self.width = width
        self.height = height
        self.fps = fps
        self.compress = compress
        self.version = version
        self.frame_count = 1

        self.tags = []

    def __getitem__(self, i):
        return self.tags.__getitem__(i)
    
    def __iadd__(self, other):
        if hasattr(other, "TAG_TYPE"):
            self.add_tag(other)
        else:
            self.add_tags(other)
        return self
    
    def add_tag(self, tag):
        if self.version > tag.TAG_MIN_VERSION:
            self.tags.append(tag)

    def add_tags(self, tag_container):
        if hasattr(tag_container, "tags"):
            self.tags += tag_container.tags
        else:
            self.tags += tag_container
    
    def serialize(self):

        header = self._gen_header()
        data = self._gen_data_stub()
        data += ''.join(tag.serialize() for tag in self.tags)
        
        header[2] = struct.pack("<L", 8 + len(data)) # FileSize
        if self.compress:
            import zlib
            data = zlib.compress(data)
            
        return "".join(header + [data])
    
    def _gen_header(self):
        return ["CWS" if self.compress else "FWS", struct.pack("<B", self.version), "\0\0\0\0"]
    
    def _gen_data_stub(self):
        data = Rect(XMax=self.width, YMax=self.height).serialize().serialize()
        return data + struct.pack("<BBH", int((self.fps - int(self.fps)) * 0x100),
                                  self.fps, self.frame_count)
