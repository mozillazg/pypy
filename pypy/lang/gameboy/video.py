"""
 PyBoy GameBoy (TM) Emulator
 constants.LCD Video Display Processor
"""

from pypy.lang.gameboy import constants

class Video(object):

    # constants.OAM Registers
    oam = [] #= new byte[OAM_SIZE]

     # Video constants.RAM
    vram = []#= new byte[VRAM_SIZE]


     # constants.LCD Registers int
    lcdc = 0
    stat = 0
    scy = 0
    scx = 0
    ly = 0
    lyc = 0
    dma = 0
    bgp = 0
    obp0 = 0
    obp1 = 0
    wy = 0
    wx = 0
    wly = 0

    cycles = 0

    frames = 0
    frameSkip = 0

    #boolean
    transfer = False
    display = False
    vblank = False
    dirty = False

     # Line Buffer, constants.OAM Cache and Color Palette
    line = []#= new int[8 + 160 + 8]
    objects = []#= new int[OBJECTS_PER_LINE]
    palette = []#= new int[1024]

     # Video Driver VideoDriver
    driver = None

     # Interrupt Controller Interrupt
    interrupt = None

     # Memory Interface Memory
    memory = None


    def __init__(self, videDriver, interrupt, memory):
        self.driver = videoDriver
        self.interrupt = interrupt
        self.memory = memory
        self.reset()


    def getFrameSkip(self):
        return self.frameSkip


    def setFrameSkip(self, frameSkip):
        self.frameSkip = frameSkip


    def reset(self):
        self.cycles = constants.MODE_2_TICKS

        self.lcdc = 0x91
        self.stat = 2
        self.ly = 0
        self.lyc = 0
        self.dma = 0xFF
        self.scy = 0
        self.scx = 0
        self.wy = self.wly = 0
        self.wx = 0
        self.bgp = 0xFC
        self.obp0 = self.obp1 = 0xFF

        self.transfer = True
        self.display = True
        self.vblank = True
        self.dirty = True

        for index in range(0, constants.VRAM_SIZE):
            self.vram[index] = 0x00

        for index in range(0, constants.OAM_SIZE):
            self.oam[index] = 0x00


    def write(self, address, data):
        # assert data >= 0x00 and data <= 0xFF
        if address == constants.LCDC :
            self.setControl(data)
        elif address == constants.STAT:
            self.setStatus(data)
        elif address == constants.SCY:
            self.setScrollY(data)
        elif address == constants.SCX:
            self.setScrollX(data)
        elif address == constants.LY:
            # Read Only
            pass
        elif address == constants.LYC:
            self.setLYCompare(data)
        elif address == constants.DMA:
            self.setDMA(data)
        elif address == constants.BGP:
            self.setBackgroundPalette(data)
        elif address == constants.OBP0:
            self.setObjectPalette0(data)
        elif address == constants.OBP1:
            self.setObjectPalette1(data)
        elif address == constants.WY:
            self.setWindowY(data)
        elif address == constants.WX:
            self.setWindowX(data)
        else:
            if (address >= constants.OAM_ADDR and address < constants.OAM_ADDR + constants.OAM_SIZE):
                #TODO convert to byte
                self.oam[address - constants.OAM_ADDR] = data
            elif (address >= constants.VRAM_ADDR and address < constants.VRAM_ADDR + constants.VRAM_SIZE):
                #TODO convert to byte
                self.vram[address - constants.VRAM_ADDR] =data


    def read(self, address):
        if address == constants.LCDC:
            return self.getControl()
        elif address == constants.STAT:
            return self.getStatus()
        elif address == constants.SCY:
            return self.getScrollY()
        elif address == constants.SCX:
            return self.getScrollX()
        elif address == constants.LY:
            return self.getLineY()
        elif address == constants.LYC:
            return self.getLineYCompare()
        elif address == constants.DMA:
            return self.getDMA()
        elif address == constants.BGP:
            return self.getBackgroundPalette()
        elif address == constants.OBP0:
            return self.getObjectPalette0()
        elif address == constants.OBP1:
            return self.getObjectPalette1()
        elif address == constants.WY:
            return self.getWindowY()
        elif address == constants.WX:
            return self.getWindowX()
        else:
            if (address >= constants.OAM_ADDR and address < constants.OAM_ADDR + constants.OAM_SIZE):
                return self.oam[address - constants.OAM_ADDR] & 0xFF
            elif (address >= constants.VRAM_ADDR and address < constants.VRAM_ADDR + constants.VRAM_SIZE):
                return self.vram[address - constants.VRAM_ADDR] & 0xFF
        return 0xFF


    def cycles(self):
        return self.cycles


    def emulate(self, ticks):
        if ((self.lcdc & 0x80) != 0):
            self.cycles -= ticks
            while (self.cycles <= 0):
                switch = self.stat & 0x03
                if switch == 0:
                    self.emulateHBlank()
                elif switch == 1:
                    self.emulateVBlank()
                elif switch == 2:
                    self.emulateOAM()
                elif switch == 3:
                    self.emulateTransfer()


    def getControl(self):
        return self.lcdc


    def getStatus(self):
        return 0x80 | self.stat


    def getScrollY(self):
        return self.scy


    def getScrollX(self):
        return self.scx


    def getLineY(self):
        return self.ly


    def getLineYCompare(self):
        return self.lyc


    def getDMA(self):
        return self.dma


    def getBackgroundPalette(self):
        return self.bgp


    def getObjectPalette0(self):
        return self.obp0


    def getObjectPalette1(self):
        return self.obp1


    def getWindowY(self):
        return self.wy


    def getWindowX(self):
        return self.wx


    def setControl(self, data):
        if ((self.lcdc & 0x80) != (data & 0x80)):
            # constants.NOTE: do not reset constants.LY=LYC flag (bit 2) of the constants.STAT register (Mr.
            # Do!)
            if ((data & 0x80) != 0):
                self.stat = (self.stat & 0xFC) | 0x02
                self.cycles = constants.MODE_2_TICKS
                self.ly = 0
                self.display = False
            else:
                self.stat = (self.stat & 0xFC) | 0x00
                self.cycles = constants.MODE_1_TICKS
                self.ly = 0

                self.clearFrame()
        # don't draw window if it was not enabled and not being drawn before
        if ((self.lcdc & 0x20) == 0 and (data & 0x20) != 0 and self.wly == 0 and self.ly > self.wy):
            self.wly = 144
        self.lcdc = data


    def setStatus(self, data):
        self.stat = (self.stat & 0x87) | (data & 0x78)
        # Gameboy Bug
        if ((self.lcdc & 0x80) != 0 and (self.stat & 0x03) == 0x01 and (self.stat & 0x44) != 0x44):
            self.interrupt.raiseInterrupt(constants.LCD)


    def setScrollY(self, data):
        self.scy = data


    def setScrollX(self, data):
        self.scx = data


    def setLYCompare(self, data):
        self.lyc = data
        if ((self.lcdc & 0x80) != 0):
            if (self.ly == self.lyc):
                # constants.NOTE: raise interrupt once per line (Prehistorik Man, The
                # Jetsons, Muhammad Ali)
                if ((self.stat & 0x04) == 0):
                    # constants.LYC=LY interrupt
                    self.stat |= 0x04
                    if ((self.stat & 0x40) != 0):
                        self.interrupt.raiseInterrupt(constants.LCD)
            else:
                self.stat &= 0xFB


    def setDMA(self, data):
        self.dma = data
        for index in range(0, constants.OAM_SIZE):
            #TODO convert to byte
            self.oam[index] = self.memory.read((self.dma << 8) + index)


    def setBackgroundPalette(self, data):
        if (self.bgp != data):
            self.bgp = data
            self.dirty = True


    def setObjectPalette0(self, data):
        if (self.obp0 != data):
            self.obp0 = data
            self.dirty = True


    def setObjectPalette1(self, data):
        if (self.obp1 != data):
            self.obp1 = data
            self.dirty = True


    def setWindowY(self, data):
        self.wy = data


    def setWindowX(self, data):
        self.wx = data


    def emulateOAM(self):
        self.stat = (self.stat & 0xFC) | 0x03
        self.cycles += constants.MODE_3_BEGIN_TICKS
        self.transfer = True


    def emulateTransfer(self):
        if (self.transfer):
            if (self.display):
                self.drawLine()
            self.stat = (self.stat & 0xFC) | 0x03
            self.cycles += constants.MODE_3_END_TICKS
            self.transfer = False
        else:
            self.stat = (self.stat & 0xFC) | 0x00
            self.cycles += constants.MODE_0_TICKS
            # H-Blank interrupt
            if ((self.stat & 0x08) != 0 and (self.stat & 0x44) != 0x44):
                self.interrupt.raiseInterrupt(constants.LCD)


    def emulateHBlank(self):
        self.ly+=1
        if (self.ly == self.lyc):
            # constants.LYC=LY interrupt
            self.stat |= 0x04
            if ((self.stat & 0x40) != 0):
                self.interrupt.raiseInterrupt(constants.LCD)
        else:
            self.stat &= 0xFB
        if (self.ly < 144):
            self.stat = (self.stat & 0xFC) | 0x02
            self.cycles += constants.MODE_2_TICKS
            # constants.OAM interrupt
            if ((self.stat & 0x20) != 0 and (self.stat & 0x44) != 0x44):
                self.interrupt.raiseInterrupt(constants.LCD)
        else:
            if (self.display):
                self.drawFrame()
            self.frames += 1
            if (self.frames >= self.frameSkip):
                self.display = True
                self.frames = 0
            else:
                self.display = False

            self.stat = (self.stat & 0xFC) | 0x01
            self.cycles += constants.MODE_1_BEGIN_TICKS
            self.vblank = True


    def emulateVBlank(self):
        if (self.vblank):
            self.vblank = False
            self.stat = (self.stat & 0xFC) | 0x01
            self.cycles += constants.MODE_1_TICKS - constants.MODE_1_BEGIN_TICKS
            # V-Blank interrupt
            if ((self.stat & 0x10) != 0):
                self.interrupt.raiseInterrupt(constants.LCD)
            # V-Blank interrupt
            self.interrupt.raiseInterrupt(constants.VBLANK)
        elif (self.ly == 0):
            self.stat = (self.stat & 0xFC) | 0x02
            self.cycles += constants.MODE_2_TICKS
            # constants.OAM interrupt
            if ((self.stat & 0x20) != 0 and (self.stat & 0x44) != 0x44):
                self.interrupt.raiseInterrupt(constants.LCD)
        else:
            if (self.ly < 153):
                self.ly+=1
                self.stat = (self.stat & 0xFC) | 0x01
                if (self.ly == 153):
                    self.cycles += constants.MODE_1_END_TICKS
                else:
                    self.cycles += constants.MODE_1_TICKS
            else:
                self.ly = self.wly = 0
                self.stat = (self.stat & 0xFC) | 0x01
                self.cycles += constants.MODE_1_TICKS - constants.MODE_1_END_TICKS
            if (self.ly == self.lyc):
                # constants.LYC=LY interrupt
                self.stat |= 0x04
                if ((self.stat & 0x40) != 0):
                    self.interrupt.raiseInterrupt(constants.LCD)
            else:
                self.stat &= 0xFB


    def drawFrame(self):
        self.driver.display()


    def clearFrame(self):
        self.clearPixels()
        self.driver.display()


    def drawLine(self):
        if ((self.lcdc & 0x01) != 0):
            self.drawBackground()
        else:
            self.drawCleanBackground()
        if ((self.lcdc & 0x20) != 0):
            self.drawWindow()
        if ((self.lcdc & 0x02) != 0):
            self.drawObjects()
        self.drawPixels()


    def drawCleanBackground(self):
        for x in range(0, 8+160+8):
            self.line[x] = 0x00


    def drawBackground(self):
        y = (self.scy + self.ly) & 0xFF
        x = self.scx & 0xFF
        tileMap = constants.VRAM_MAP_A
        if (self.lcdc & 0x08) != 0:
            tileMap =  constants.VRAM_MAP_B
        tileData = constants.VRAM_DATA_B
        if (self.lcdc & 0x10) != 0:
            tileData = constants.VRAM_DATA_A
        tileMap += ((y >> 3) << 5) + (x >> 3)
        tileData += (y & 7) << 1
        self.drawTiles(8 - (x & 7), tileMap, tileData)


    def drawWindow(self):
        if (self.ly >= self.wy and self.wx < 167 and self.wly < 144):
            tileMap = constants.VRAM_MAP_A
            if (self.lcdc & 0x40) != 0:
                tileMap =  constants.VRAM_MAP_B
            tileData = constants.VRAM_DATA_B
            if (self.lcdc & 0x10) != 0:
                tileData = constants.VRAM_DATA_A
            tileMap += (self.wly >> 3) << 5
            tileData += (self.wly & 7) << 1
            self.drawTiles(self.wx + 1, tileMap, tileData)
            self.wly+=1


    def drawObjects(self):
        count = self.scanObjects()
        lastx = 176
        for index in range(176, count):
            data = self.objects[index]
            x = (data >> 24) & 0xFF
            flags = (data >> 12) & 0xFF
            address = data & 0xFFF
            if (x + 8 <= lastx):
                self.drawObjectTile(x, address, flags)
            else:
                self.drawOverlappedObjectTile(x, address, flags)
            lastx = x


    def scanObjects(self):
        count = 0
        # search active objects
        for offset in range(0, 4*40, 4):
            y = self.oam[offset + 0] & 0xFF
            x = self.oam[offset + 1] & 0xFF
            if (y <= 0 or y >= 144 + 16 or x <= 0 or x >= 168):
                continue
            tile = self.oam[offset + 2] & 0xFF
            flags = self.oam[offset + 3] & 0xFF

            y = self.ly - y + 16

            if ((self.lcdc & 0x04) != 0):
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
            self.objects[count] = (x << 24) + (count << 20) + (flags << 12) + ((tile << 4) + (y << 1))
            if (++count >= constants.OBJECTS_PER_LINE):
                break
        self.sortScanObject(count)
        return count

    def sortScanObject(self, count):
        # sort objects from lower to higher priority
        for index in range(0, count):
            rightmost = index
            for number in range(index+1, count):
                if ((self.objects[number] >> 20) > (self.objects[rightmost] >> 20)):
                    rightmost = number
            if (rightmost != index):
                data = self.objects[index]
                self.objects[index] = self.objects[rightmost]
                self.objects[rightmost] = data


    def drawTiles(self, x, tileMap, tileData):
        if ((self.lcdc & 0x10) != 0):
            while (x < 168):
                tile = self.vram[tileMap] & 0xFF
                self.drawTile(x, tileData + (tile << 4))
                tileMap = (tileMap & 0x1FE0) + ((tileMap + 1) & 0x001F)
                x += 8
        else:
            while (x < 168):
                tile = (self.vram[tileMap] ^ 0x80) & 0xFF
                self.drawTile(x, tileData + (tile << 4))
                tileMap = (tileMap & 0x1FE0) + ((tileMap + 1) & 0x001F)
                x += 8


    def drawTile(self, x, address):
        pattern = (self.vram[address] & 0xFF) + ((self.vram[address + 1] & 0xFF) << 8)
        self.line[x + 0] = (pattern >> 7) & 0x0101
        self.line[x + 1] = (pattern >> 6) & 0x0101
        self.line[x + 2] = (pattern >> 5) & 0x0101
        self.line[x + 3] = (pattern >> 4) & 0x0101
        self.line[x + 4] = (pattern >> 3) & 0x0101
        self.line[x + 5] = (pattern >> 2) & 0x0101
        self.line[x + 6] = (pattern >> 1) & 0x0101
        self.line[x + 7] = (pattern >> 0) & 0x0101


    def drawObjectTile(self, x, address, flags):
        pattern = (self.vram[address] & 0xFF) + ((self.vram[address + 1] & 0xFF) << 8)
        mask = 0
        # priority
        if (flags & 0x80) != 0:
            mask |= 0x0008
        # palette
        if (flags & 0x10) != 0:
            mask |= 0x0004
        # X flip
        if (flags & 0x20) != 0:
            color = (pattern << 1)
            if ((color & 0x0202) != 0):
                self.line[x + 0] |= color | mask
            color = (pattern >> 0)
            if ((color & 0x0202) != 0):
                self.line[x + 1] |= color | mask
            color = (pattern >> 1)
            if ((color & 0x0202) != 0):
                self.line[x + 2] |= color | mask
            color = (pattern >> 2)
            if ((color & 0x0202) != 0):
                self.line[x + 3] |= color | mask
            color = (pattern >> 3)
            if ((color & 0x0202) != 0):
                self.line[x + 4] |= color | mask
            color = (pattern >> 4)
            if ((color & 0x0202) != 0):
                self.line[x + 5] |= color | mask
            color = (pattern >> 5)
            if ((color & 0x0202) != 0):
                self.line[x + 6] |= color | mask
            color = (pattern >> 6)
            if ((color & 0x0202) != 0):
                self.line[x + 7] |= color | mask
        else:
            color = (pattern >> 6)
            if ((color & 0x0202) != 0):
                self.line[x + 0] |= color | mask
            color = (pattern >> 5)
            if ((color & 0x0202) != 0):
                self.line[x + 1] |= color | mask
            color = (pattern >> 4)
            if ((color & 0x0202) != 0):
                self.line[x + 2] |= color | mask
            color = (pattern >> 3)
            if ((color & 0x0202) != 0):
                self.line[x + 3] |= color | mask
            color = (pattern >> 2)
            if ((color & 0x0202) != 0):
                self.line[x + 4] |= color | mask
            color = (pattern >> 1)
            if ((color & 0x0202) != 0):
                self.line[x + 5] |= color | mask
            color = (pattern >> 0)
            if ((color & 0x0202) != 0):
                self.line[x + 6] |= color | mask
            color = (pattern << 1)
            if ((color & 0x0202) != 0):
                self.line[x + 7] |= color | mask


    def drawOverlappedObjectTile(self, x, address, flags):
        pattern = (self.vram[address] & 0xFF) + ((self.vram[address + 1] & 0xFF) << 8)
        mask = 0
        # priority
        if ((flags & 0x80) != 0):
            mask |= 0x0008
        # palette
        if ((flags & 0x10) != 0):
            mask |= 0x0004
        # X flip
        if ((flags & 0x20) != 0):
            color = (pattern << 1)
            if ((color & 0x0202) != 0):
                self.line[x + 0] = (self.line[x + 0] & 0x0101) | color | mask
            color = (pattern >> 0)
            if ((color & 0x0202) != 0):
                self.line[x + 1] = (self.line[x + 1] & 0x0101) | color | mask
            color = (pattern >> 1)
            if ((color & 0x0202) != 0):
                self.line[x + 2] = (self.line[x + 2] & 0x0101) | color | mask
            color = (pattern >> 2)
            if ((color & 0x0202) != 0):
                self.line[x + 3] = (self.line[x + 3] & 0x0101) | color | mask
            color = (pattern >> 3)
            if ((color & 0x0202) != 0):
                self.line[x + 4] = (self.line[x + 4] & 0x0101) | color | mask
            color = (pattern >> 4)
            if ((color & 0x0202) != 0):
                self.line[x + 5] = (self.line[x + 5] & 0x0101) | color | mask
            color = (pattern >> 6)
            if ((color & 0x0202) != 0):
                self.line[x + 7] = (self.line[x + 7] & 0x0101) | color | mask
            color = (pattern >> 5)
            if ((color & 0x0202) != 0):
                self.line[x + 6] = (self.line[x + 6] & 0x0101) | color | mask
        else:
            color = (pattern >> 6)
            if ((color & 0x0202) != 0):
                self.line[x + 0] = (self.line[x + 0] & 0x0101) | color | mask
            color = (pattern >> 5)
            if ((color & 0x0202) != 0):
                self.line[x + 1] = (self.line[x + 1] & 0x0101) | color | mask
            color = (pattern >> 4)
            if ((color & 0x0202) != 0):
                self.line[x + 2] = (self.line[x + 2] & 0x0101) | color | mask
            color = (pattern >> 3)
            if ((color & 0x0202) != 0):
                self.line[x + 3] = (self.line[x + 3] & 0x0101) | color | mask
            color = (pattern >> 2)
            if ((color & 0x0202) != 0):
                self.line[x + 4] = (self.line[x + 4] & 0x0101) | color | mask
            color = (pattern >> 1)
            if ((color & 0x0202) != 0):
                self.line[x + 5] = (self.line[x + 5] & 0x0101) | color | mask
            color = (pattern >> 0)
            if ((color & 0x0202) != 0):
                self.line[x + 6] = (self.line[x + 6] & 0x0101) | color | mask
            color = (pattern << 1)
            if ((color & 0x0202) != 0):
                self.line[x + 7] = (self.line[x + 7] & 0x0101) | color | mask


    def drawPixels(self):
        self.updatePalette()
        pixels = self.driver.getPixels()
        offset = self.ly * self.driver.getWidth()
        for x in range(8, 168, 4):
            pattern0 = self.line[x + 0]
            pattern1 = self.line[x + 1]
            pattern2 = self.line[x + 2]
            pattern3 = self.line[x + 3]
            pixels[offset + 0] = self.palette[pattern0]
            pixels[offset + 1] = self.palette[pattern1]
            pixels[offset + 2] = self.palette[pattern2]
            pixels[offset + 3] = self.palette[pattern3]
            offset += 4


    def clearPixels(self):
        pixels = self.driver.getPixels()
        length = self.driver.getWidth() * self.driver.getHeight()
        for offset in range(0, length):
            pixels[offset] = constants.COLOR_MAP[0]


    def updatePalette(self):
        if (not self.dirty):
            return
        # bit 4/0 = constants.BG color, bit 5/1 = constants.OBJ color, bit 2 = constants.OBJ palette, bit
        # 3 = constants.OBJ priority
        for pattern in range(0, 64):
            #color
            if ((pattern & 0x22) == 0 or ((pattern & 0x08) != 0 and (pattern & 0x11) != 0)):
                # constants.OBJ behind constants.BG color 1-3
                color = (self.bgp >> ((((pattern >> 3) & 0x02) + (pattern & 0x01)) << 1)) & 0x03
             # constants.OBJ above constants.BG
            elif ((pattern & 0x04) == 0):
                color = (self.obp0 >> ((((pattern >> 4) & 0x02) + ((pattern >> 1) & 0x01)) << 1)) & 0x03
            else:
                color = (self.obp1 >> ((((pattern >> 4) & 0x02) + ((pattern >> 1) & 0x01)) << 1)) & 0x03

            self.palette[((pattern & 0x30) << 4) + (pattern & 0x0F)] = constants.COLOR_MAP[color]
        self.dirty = False
