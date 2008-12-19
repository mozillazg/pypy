

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
    
    def add_tag(self, tag):
        if self.version > tag.min_version:
            self.tags.append(tag)

    def add_tags(self, tag_container):
        if hasattr(tag_container, "tags"):
            self.tags += tag_container.tags
        else:
            self.tags += tag_container
    
    def serialize(self):
        final_bytes = []

        header = __gen_header()
        data = __gen_data_stub()
        data += [tag.serialize() for tag in self.tags]
        
        header[3] = len(header) + len("".join(data)) # FileSize
        if self.compress:
            import zlib
            data = zlib.compress(data)
            
        return "".join(header + data)
        
    def __gen_header(self):
        import struct
        return ("CWS" if self.compress else "FWS") + struct.pack("BL", self.version, 0)
            
    def __gen_data_stub(self):
        from util import BitStream
        from records import Rect
        data = BitStream()
        data += Rect(XMax=width, YMax=height).serialize()
        data.write_bit_value(fps, 16)
        data.write_bit_value(frame_count, 16)
        return data.serialize()
