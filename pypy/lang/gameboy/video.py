"""
 PyBoy GameBoy (TM) Emulator
 constants.LCD Video Display Processor
"""

from pypy.lang.gameboy import constants
from pypy.lang.gameboy.ram import iMemory

class Video(iMemory):
    #frames = 0
    #frame_skip = 0

     # Line Buffer, constants.OAM Cache and Color Palette
    #line = []#= new int[8 + 160 + 8]
    #objects = []#= new int[OBJECTS_PER_LINE]
    #palette = []#= new int[1024]

    def __init__(self, video_driver, interrupt, memory):
        assert isinstance(video_driver, VideoDriver)
        self.driver = video_driver
        self.interrupt = interrupt
        self.memory = memory
        self.reset()

    def get_frame_skip(self):
        return self.frame_skip

    def set_frame_skip(self, frame_skip):
        self.frame_skip = frame_skip

    def reset(self):
        self.cycles     = constants.MODE_2_TICKS
        self.control    = 0x91
        self.stat       = 2
        self.line_y     = 0
        self.line_y_compare = 0
        self.dma        = 0xFF
        self.scroll_y   = 0
        self.scroll_x   = 0
        self.window_y   = self.wline_y = 0
        self.window_x   = 0
        self.background_palette = 0xFC
        self.object_palette_0   = 0xFF 
        self.object_palette_1   = 0xFF

        self.transfer   = True
        self.display    = True
        self.vblank     = True
        self.dirty      = True

        self.vram       = [0]*constants.VRAM_SIZE
        self.oam        = [0]*constants.OAM_SIZE
        
        self.line       = [0]* (8+160+8)
        self.objects    = [0] * constants.OBJECTS_PER_LINE
        self.palette    = [0] * 1024
        
        self.frames     = 0
        self.frame_skip = 0

    def write(self, address, data):
        address = int(address)
        # assert data >= 0x00 and data <= 0xFF
        if address == constants.LCDC :
            self.set_control(data)
        elif address == constants.STAT:
            self.set_status(data)
        elif address == constants.SCY:
            self.set_scroll_y(data)
        elif address == constants.SCX:
            self.set_scroll_x(data)
        elif address == constants.LY:
            # Read Online_y
            pass
        elif address == constants.LYC:
            self.set_ly_compare(data)
        elif address == constants.DMA:
            self.set_dma(data)
        elif address == constants.BGP:
            self.set_background_palette(data)
        elif address == constants.OBP0:
            self.set_object_palette_0(data)
        elif address == constants.OBP1:
            self.set_object_palette_1(data)
        elif address == constants.WY:
            self.set_window_y(data)
        elif address == constants.WX:
            self.set_window_x(data)
        else:
            self.write_oam(address, data)

    def write_oam(self, address, data):
        if address >= constants.OAM_ADDR and \
           address < constants.OAM_ADDR + constants.OAM_SIZE:
            self.oam[address - constants.OAM_ADDR] = data & 0xFF
        elif address >= constants.VRAM_ADDR and \
             address < constants.VRAM_ADDR + constants.VRAM_SIZE:
              self.vram[address - constants.VRAM_ADDR] = data & 0xFF
            
    def read(self, address):
        address = int(address)
        if address == constants.LCDC:
            return self.get_control()
        elif address == constants.STAT:
            return self.get_status()
        elif address == constants.SCY:
            return self.get_scroll_y()
        elif address == constants.SCX:
            return self.get_scroll_x()
        elif address == constants.LY:
            return self.get_line_y()
        elif address == constants.LYC:
            return self.get_line_y_compare()
        elif address == constants.DMA:
            return self.get_dma()
        elif address == constants.BGP:
            return self.get_background_palette()
        elif address == constants.OBP0:
            return self.get_object_palette_0()
        elif address == constants.OBP1:
            return self.get_object_palette_1()
        elif address == constants.WY:
            return self.get_window_y()
        elif address == constants.WX:
            return self.get_window_x()
        else:
            return self.read_oam(address)
        
    def read_oam(self, address):
        if (address >= constants.OAM_ADDR and \
            address < constants.OAM_ADDR + constants.OAM_SIZE):
             return self.oam[address - constants.OAM_ADDR]
        elif (address >= constants.VRAM_ADDR and \
            address < constants.VRAM_ADDR + constants.VRAM_SIZE):
             return self.vram[address - constants.VRAM_ADDR]
        return 0xFF

    def get_cycles(self):
        return self.cycles

    def emulate(self, ticks):
        ticks = int(ticks)
        if (self.control & 0x80) != 0:
            self.cycles -= ticks
            self.consume_cycles()
            
    def consume_cycles(self):
        while self.cycles <= 0:
            if self.stat == 0:
                self.emulate_hblank()
            elif self.stat == 1:
                self.emulate_vblank()
            elif self.stat == 2:
                self.emulate_oam()
            else:
                self.emulate_transfer()

    def get_control(self):
        return self.control

    def set_control(self, data):
        if (self.control & 0x80) != (data & 0x80):
            self.reset_control(data)
        # don't draw window if it was not enabled and not being drawn before
        if (self.control & 0x20) == 0 and (data & 0x20) != 0 and \
           self.wline_y == 0 and self.line_y > self.window_y:
             self.wline_y = 144
        self.control = data

    def reset_control(self, data):
        # NOTE: do not reset constants.LY=LYC flag (bit 2) of the STAT register (Mr. Do!)
        if (data & 0x80) != 0:
            self.stat = (self.stat & 0xFC) | 0x02
            self.cycles = constants.MODE_2_TICKS
            self.line_y = 0
            self.display = False
        else:
            self.stat = (self.stat & 0xFC) | 0x00
            self.cycles = constants.MODE_1_TICKS
            self.line_y = 0
            self.clear_frame()
                
    def get_status(self):
        return 0x80 | self.stat

    def set_status(self, data):
        self.stat = (self.stat & 0x87) | (data & 0x78)
        # Gameboy Bug
        if (self.control & 0x80) != 0 and (self.stat & 0x03) == 0x01 and \
           (self.stat & 0x44) != 0x44:
             self.interrupt.raise_interrupt(constants.LCD)

    def get_scroll_y(self):
        return self.scroll_y
                
    def set_scroll_y(self, data):
        self.scroll_y = data
        
    def get_scroll_x(self):
        return self.scroll_x

    def set_scroll_x(self, data):
        self.scroll_x = data
        
    def get_line_y(self):
        return self.line_y

    def get_line_y_compare(self):
        return self.line_y_compare

    def set_ly_compare(self, data):
        self.line_y_compare = data
        if (self.control & 0x80) == 0:
            return
        if self.line_y == self.line_y_compare:
            # NOTE: raise interrupt once per line
            if (self.stat & 0x04) == 0:
                # constants.LYC=LY interrupt
                self.stat |= 0x04
#                if (self.stat & 0x40) != 0:
                self.interrupt.raise_interrupt(constants.LCD)
        else:
            self.stat &= 0xFB
                
    def get_dma(self):
        return self.dma

    def set_dma(self, data):
        self.dma = data
        for index in range(0, constants.OAM_SIZE):
            self.oam[index] = self.memory.read((self.dma << 8) + index)

    def get_background_palette(self):
        return self.background_palette

    def set_background_palette(self, data):
        if self.background_palette != data:
            self.background_palette = data
            self.dirty = True

    def get_object_palette_0(self):
        return self.object_palette_0

    def set_object_palette_0(self, data):
        if self.object_palette_0 != data:
            self.object_palette_0 = data
            self.dirty = True

    def get_object_palette_1(self):
        return self.object_palette_1

    def set_object_palette_1(self, data):
        if self.object_palette_1 != data:
            self.object_palette_1 = data
            self.dirty = True

    def get_window_y(self):
        return self.window_y

    def set_window_y(self, data):
        self.window_y = data
        
    def get_window_x(self):
        return self.window_x

    def set_window_x(self, data):
        self.window_x = data

    def emulate_oam(self):
        self.stat = (self.stat & 0xFC) | 0x03
        self.cycles += constants.MODE_3_BEGIN_TICKS
        self.transfer = True

    def emulate_transfer(self):
        if self.transfer:
            if self.display:
                self.draw_line()
            self.stat = (self.stat & 0xFC) | 0x03
            self.cycles += constants.MODE_3_END_TICKS
            self.transfer = False
        else:
            self.stat = (self.stat & 0xFC)
            self.cycles += constants.MODE_0_TICKS
            # H-Blank interrupt
            if (self.stat & 0x08) != 0 and (self.stat & 0x44) != 0x44:
                self.interrupt.raise_interrupt(constants.LCD)

    def emulate_hblank(self):
        self.line_y+=1
        self.emulate_hblank_line_y_compare()
        if self.line_y < 144:
            self.emulate_hblank_part_1()
        else:
            self.emulate_hblank_part_2()
            
    def emulate_hblank_line_y_compare(self):
        if self.line_y == self.line_y_compare:
            # constants.LYC=LY interrupt
            self.stat |= 0x04
            if (self.stat & 0x40) != 0:
                self.interrupt.raise_interrupt(constants.LCD)
        else:
            self.stat &= 0xFB
            
    def emulate_hblank_part_1(self):
        self.stat = (self.stat & 0xFC) | 0x02
        self.cycles += constants.MODE_2_TICKS
        # constants.OAM interrupt
        if (self.stat & 0x20) != 0 and (self.stat & 0x44) != 0x44:
            self.interrupt.raise_interrupt(constants.LCD)
        
    def emulate_hblank_part_2(self):
        if self.display:
            self.draw_frame()
        self.frames += 1
        if self.frames >= self.frame_skip:
            self.display = True
            self.frames = 0
        else:
            self.display = False

        self.stat = (self.stat & 0xFC) | 0x01
        self.cycles += constants.MODE_1_BEGIN_TICKS
        self.vblank = True
        
    def emulate_vblank(self):
        if self.vblank:
            self.emulate_vblank_vblank()
        elif self.line_y == 0:
            self.emulate_vblank_first_y_line()
        else:
            self.emulate_vblank_other()

    def emulate_vblank_vblank(self):
        self.vblank = False
        self.stat = (self.stat & 0xFC) | 0x01
        self.cycles += constants.MODE_1_TICKS - constants.MODE_1_BEGIN_TICKS
        # V-Blank interrupt
        if (self.stat & 0x10) != 0:
            self.interrupt.raise_interrupt(constants.LCD)
        # V-Blank interrupt
        self.interrupt.raise_interrupt(constants.VBLANK)
        
    def emulate_vblank_first_y_line(self):
        self.stat = (self.stat & 0xFC) | 0x02
        self.cycles += constants.MODE_2_TICKS
        # constants.OAM interrupt
        if (self.stat & 0x20) != 0 and (self.stat & 0x44) != 0x44:
            self.interrupt.raise_interrupt(constants.LCD)
            
    def emulate_vblank_other(self):
        if self.line_y < 153:
            self.line_y+=1
            self.stat = (self.stat & 0xFC) | 0x01
            if self.line_y == 153:
                self.cycles += constants.MODE_1_END_TICKS
            else:
                self.cycles += constants.MODE_1_TICKS
        else:
            self.line_y = self.wline_y = 0
            self.stat = (self.stat & 0xFC) | 0x01
            self.cycles += constants.MODE_1_TICKS - constants.MODE_1_END_TICKS
        if self.line_y == self.line_y_compare:
            # constants.LYC=LY interrupt
            self.stat |= 0x04
            if (self.stat & 0x40) != 0:
                self.interrupt.raise_interrupt(constants.LCD)
        else:
            self.stat &= 0xFB
    
    def draw_frame(self):
        self.driver.update_display()

    def clear_frame(self):
        self.clear_pixels()
        self.driver.update_display()

    def draw_line(self):
        if (self.control & 0x01) != 0:
            self.draw_background()
        else:
            self.draw_clean_background()
        if (self.control & 0x20) != 0:
            self.draw_window()
        if (self.control & 0x02) != 0:
            self.draw_objects()
        self.draw_pixels()

    def draw_clean_background(self):
        for x in range(0, 8+160+8):
            self.line[x] = 0x00

    def draw_background(self):
        y = (self.scroll_y + self.line_y) & 0xFF
        x = self.scroll_x & 0xFF
        tileMap = constants.VRAM_MAP_A
        if (self.control & 0x08) != 0:
            tileMap =  constants.VRAM_MAP_B
        tileData = constants.VRAM_DATA_B
        if (self.control & 0x10) != 0:
            tileData = constants.VRAM_DATA_A
        tileMap  += ((y >> 3) << 5) + (x >> 3)
        tileData += (y & 7) << 1
        self.draw_tiles(8 - (x & 7), tileMap, tileData)

    def draw_window(self):
        if self.line_y < self.window_y or self.window_x >= 167 or \
           self.wline_y >= 144:
            return
        tileMap = constants.VRAM_MAP_A
        if (self.control & 0x40) != 0:
            tileMap =  constants.VRAM_MAP_B
        tileData = constants.VRAM_DATA_B
        if (self.control & 0x10) != 0:
            tileData = constants.VRAM_DATA_A
        tileMap += (self.wline_y >> 3) << 5
        tileData += (self.wline_y & 7) << 1
        self.draw_tiles(self.window_x + 1, tileMap, tileData)
        self.wline_y+=1

    def draw_objects(self):
        count = self.scan_objects()
        lastx = 176
        for index in range(176, count):
            data = self.objects[index]
            x = (data >> 24) & 0xFF
            flags = (data >> 12) & 0xFF
            address = data & 0xFFF
            if (x + 8 <= lastx):
                self.draw_object_tile(x, address, flags)
            else:
                self.draw_overlapped_object_tile(x, address, flags)
            lastx = x

    def scan_objects(self):
        count = 0
        # search active objects
        for offset in range(0, 4*40, 4):
            y = self.oam[offset + 0] & 0xFF
            x = self.oam[offset + 1] & 0xFF
            if (y <= 0 or y >= 144 + 16 or x <= 0 or x >= 168):
                continue
            tile = self.oam[offset + 2] & 0xFF
            flags = self.oam[offset + 3] & 0xFF

            y = self.line_y - y + 16

            if ((self.control & 0x04) != 0):
                # 8x16 tile size
                if (y < 0 or y > 15):
                    continue
                # Y flip
                if ((flags & 0x40) != 0):
                    y = 15 - y
                tile &= 0xFE
            else:
                # 8x8 tile size
                if (y < 0 or y > 7):
                    continue
                # Y flip
                if ((flags & 0x40) != 0):
                    y = 7 - y
            self.objects[count] = (x << 24) + (count << 20) + (flags << 12) + \
                                  (tile << 4) + (y << 1)
            count += 1
            if count >= constants.OBJECTS_PER_LINE:
                break
        self.sort_scan_object(count)
        return count

    def sort_scan_object(self, count):
        # sort objects from lower to higher priority
        for index in range(0, count):
            rightmost = index
            for number in range(index+1, count):
                if (self.objects[number] >> 20) > \
                   (self.objects[rightmost] >> 20):
                    rightmost = number
            if rightmost != index:
                data = self.objects[index]
                self.objects[index] = self.objects[rightmost]
                self.objects[rightmost] = data

    def draw_tiles(self, x, tileMap, tileData):
        while x < 168:
            if (self.control & 0x10) != 0:
                tile = self.vram[tileMap] & 0xFF
            else:
                tile = (self.vram[tileMap] ^ 0x80) & 0xFF
            self.draw_tile(x, tileData + (tile << 4))
            tileMap = (tileMap & 0x1FE0) + ((tileMap + 1) & 0x001F)
            x += 8
            
    def get_pattern(self, address):
        pattern = self.vram[address]      & 0xFF
        pattern += (self.vram[address + 1] & 0xFF) << 8
        return pattern

    def draw_object(self, setter):
        pattern = self.get_pattern(address)
        self.mask = 0
        # priority
        if (flags & 0x80) != 0:
            self.mask |= 0x0008
        # palette
        if (flags & 0x10) != 0:
            self.mask |= 0x0004
        if (flags & 0x20) != 0:
            self.draw_object_normal(x, pattern, mask, setter)
        else:
            self.draw_object_flipped(x, pattern, mask, setter)
            
    def draw_object_normal(self, x, pattern, mask, setter):
        for i in range(0, 7):
            color = pattern >> (6-i)
            if (color & 0x0202) != 0:
                setter(self, x+1, color, mask)
        color = pattern << 1
        if (color & 0x0202) != 0:
            setter(self, x+7, color,  mask)
        
    def draw_object_flipped(self, x, pattern, mask, setter):
        color = pattern << 1
        if (color & 0x0202) != 0:
            setter(self, x, color | mask)
        for i in range(0, 7):
            color = pattern >> i
            if (color & 0x0202) != 0:
                setter(self, x + i + 1, color | mask)
            
    def draw_tile(self, x, address):
        pattern =  self.get_pattern(address)
        for i in range(0, 8):
            self.line[x + i] = (pattern >> (7-i)) & 0x0101

    def draw_object_tile(self, x, address, flags):
        pattern = self.get_pattern(address)
        self.draw_object(self.setTileLine)
        
    def set_tile_line(self, pos, color, mask):
        self.line[pos] |= color | mask

    def draw_overlapped_object_tile(self, x, address, flags):
        self.draw_object(self.setOverlappedObjectLine)
        
    def set_overlapped_object_line(self, pos, color, mask):
        self.line[pos] = (self.line[pos] & 0x0101) | color | mask

    def draw_pixels(self):
        self.update_palette()
        pixels = self.driver.get_pixels()
        offset = self.line_y * self.driver.get_width()
        for x in range(8, 168, 4):
            for i in range(0,4):
                pattern = self.line[x + i]
                pixels[offset + i] = self.palette[pattern]
            offset += 4

    def clear_pixels(self):
        self.driver.clear_pixels()

    def update_palette(self):
        if not self.dirty:
            return
        # bit 4/0 = constants.BG color, 
        # bit 5/1 = constants.OBJ color, 
        # bit 2 = constants.OBJ palette, 
        # bit 3 = constants.OBJ priority
        for pattern in range(0, 64):
            #color
            if (pattern & 0x22) == 0 or ((pattern & 0x08) != 0 and \
               (pattern & 0x11) != 0):
                # constants.OBJ behind constants.BG color 1-3
                color = (self.background_palette >> ((((pattern >> 3) & 0x02) +\
                        (pattern & 0x01)) << 1)) & 0x03
             # constants.OBJ above constants.BG
            elif ((pattern & 0x04) == 0):
                color = (self.object_palette_0 >> ((((pattern >> 4) & 0x02) + \
                        ((pattern >> 1) & 0x01)) << 1)) & 0x03
            else:
                color = (self.object_palette_1 >> ((((pattern >> 4) & 0x02) +\
                        ((pattern >> 1) & 0x01)) << 1)) & 0x03
            index= ((pattern & 0x30) << 4) + (pattern & 0x0F)
            self.palette[index] = constants.COLOR_MAP[color]
        self.dirty = False

# ------------------------------------------------------------------------------

class VideoDriver(object):
    
    def __init__(self):
        self.width = int(constants.GAMEBOY_SCREEN_WIDTH)
        self.height = int(constants.GAMEBOY_SCREEN_HEIGHT)
        self.clear_pixels()
        
    def clear_pixels(self):
        self.pixels = [0] * self.width * self.height
            
    def get_width(self):
        return self.width
    
    def get_height(self):
        return selg.height
    
    def get_pixels(self):
        return self.pixels
    
    def update_display(self):
        self.clear_pixels()
        