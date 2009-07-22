from pypy.jit.metainterp.history import Box

# Logic to encode the chain of frames and the state of the boxes at a
# FAIL operation, and to decode it again.  This is a bit advanced,
# because it needs to support optimize.py which encodes virtuals with
# arbitrary cycles.

# XXX I guess that building the data so that it is compact as possible
# would be a big win.


class ResumeDataBuilder(object):

    def __init__(self):
        self.memo = {}
        self.liveboxes = []
        self.consts = []
        self.nums = []
        self.frame_infos = []

    def generate_boxes(self, boxes):
        for box in boxes:
            assert box is not None
            if isinstance(box, Box):
                try:
                    num = self.memo[box]
                except KeyError:
                    num = len(self.liveboxes)
                    self.liveboxes.append(box)
                    self.memo[box] = num
            else:
                num = -2 - len(self.consts)
                self.consts.append(box)
            self.nums.append(num)
        self.nums.append(-1)

    def generate_frame_info(self, *frame_info):
        self.frame_infos.append(frame_info)

    def finish(self, storage):
        storage.rd_frame_infos = self.frame_infos[:]
        storage.rd_nums = self.nums[:]
        storage.rd_consts = self.consts[:]
        return self.liveboxes


class ResumeDataReader(object):
    i_frame_infos = 0
    i_boxes = 0

    def __init__(self, storage, liveboxes):
        self.frame_infos = storage.rd_frame_infos
        self.nums = storage.rd_nums
        self.consts = storage.rd_consts
        self.liveboxes = liveboxes

    def consume_boxes(self):
        boxes = []
        while True:
            num = self.nums[self.i_boxes]
            self.i_boxes += 1
            if num >= 0:
                box = self.liveboxes[num]
            elif num != -1:
                box = self.consts[-2 - num]
            else:
                break
            boxes.append(box)
        return boxes

    def has_more_frame_infos(self):
        return self.i_frame_infos < len(self.frame_infos)

    def consume_frame_info(self):
        frame_info = self.frame_infos[self.i_frame_infos]
        self.i_frame_infos += 1
        return frame_info
