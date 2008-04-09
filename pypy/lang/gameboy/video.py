"""
 PyBoy GameBoy (TM) Emulator
 constants.LCD Video Display Processor
"""

from pypy.lang.gameboy import constants

class Video(object):
    #frames = 0
    #frameSkip = 0

     # Line Buffer, constants.OAM Cache and Color Palette
    #line = []#= new int[8 + 160 + 8]
    #objects = []#= new int[OBJECTS_PER_LINE]
    #palette = []#= new int[1024]


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

        self.control = 0x91
        self.stat = 2
        self.lineY = 0
        self.lineYCompare = 0
        self.dma = 0xFF
        self.scrollY = 0
        self.scrollX = 0
        self.windowY = self.wlineY = 0
        self.windowX = 0
        self.backgroundPalette = 0xFC
        self.objectPalette0 = self.objectPalette1 = 0xFF

        self.transfer = True
        self.display = True
        self.vblank = True
        self.dirty = True

        self.vram = [0]*constants.VRAM_SIZE
        self.oam = [0]*constants.OAM_SIZE
        
        self.line = [0]* (8+160+8)
        self.objects = [0] * constants.OBJECTS_PER_LINE
        self.palette = [0] * 1024
        
        self.frames = 0
        self.frameSkip = 0

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
            # Read OnlineY
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
            self.writeOAM(address, data)

    def writeOAM(self, address, data):
        if (address >= constants.OAM_ADDR and address < constants.OAM_ADDR + constants.OAM_SIZE):
            self.oam[address - constants.OAM_ADDR] = data & 0xFF
        elif (address >= constants.VRAM_ADDR and address < constants.VRAM_ADDR + constants.VRAM_SIZE):
            self.vram[address - constants.VRAM_ADDR] = data & 0xFF
            
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
            return self.readOAM(address)
        
        
    def readOAM(self, address):
        if (address >= constants.OAM_ADDR and address < constants.OAM_ADDR + constants.OAM_SIZE):
            return self.oam[address - constants.OAM_ADDR]
        elif (address >= constants.VRAM_ADDR and address < constants.VRAM_ADDR + constants.VRAM_SIZE):
            return self.vram[address - constants.VRAM_ADDR]
        return 0xFF

    def getCycles(self):
        return self.cycles

    def emulate(self, ticks):
        if (self.control & 0x80) != 0:
            self.cycles -= ticks
            self.consumeCycles()
            
    def consumeCycles(self):
        while (self.cycles <= 0):
            if self.stat == 0:
                self.emulateHBlank()
            elif self.stat == 1:
                self.emulateVBlank()
            elif self.stat == 2:
                self.emulateOAM()
            else:
                self.emulateTransfer()


    def getControl(self):
        return self.control

    def setControl(self, data):
        if (self.control & 0x80) != (data & 0x80):
            self.resetControl(data)
        # don't draw window if it was not enabled and not being drawn before
        if ((self.control & 0x20) == 0 and (data & 0x20) != 0 and self.wlineY == 0 and self.lineY > self.windowY):
            self.wlineY = 144
        self.control = data

    def resetControl(self, data):
            # NOTE: do not reset constants.LY=LYC flag (bit 2) of the STAT register (Mr. Do!)
            if (data & 0x80) != 0:
                self.stat = (self.stat & 0xFC) | 0x02
                self.cycles = constants.MODE_2_TICKS
                self.lineY = 0
                self.display = False
            else:
                self.stat = (self.stat & 0xFC) | 0x00
                self.cycles = constants.MODE_1_TICKS
                self.lineY = 0
                self.clearFrame()
                
    def getStatus(self):
        return 0x80 | self.stat

    def setStatus(self, data):
        self.stat = (self.stat & 0x87) | (data & 0x78)
        # Gameboy Bug
        if ((self.control & 0x80) != 0 and (self.stat & 0x03) == 0x01 and (self.stat & 0x44) != 0x44):
            self.interrupt.raiseInterrupt(constants.LCD)

    def getScrollY(self):
        return self.scrollY
                
    def setScrollY(self, data):
        self.scrollY = data
        
    def getScrollX(self):
        return self.scrollX

    def setScrollX(self, data):
        self.scrollX = data
        
    def getLineY(self):
        return self.lineY

    def getLineYCompare(self):
        return self.lineYCompare

    def setLYCompare(self, data):
        self.lineYCompare = data
        if ((self.control & 0x80) != 0):
            if (self.lineY == self.lineYCompare):
                # NOTE: raise interrupt once per line (Prehistorik Man, The Jetsons, Muhammad Ali)
                if ((self.stat & 0x04) == 0):
                    # constants.LYC=LY interrupt
                    self.stat |= 0x04
                    if ((self.stat & 0x40) != 0):
                        self.interrupt.raiseInterrupt(constants.LCD)
            else:
                self.stat &= 0xFB
                
    def getDMA(self):
        return self.dma

    def setDMA(self, data):
        self.dma = data
        for index in range(0, constants.OAM_SIZE):
            self.oam[index] = self.memory.read((self.dma << 8) + index)


    def getBackgroundPalette(self):
        return self.backgroundPalette

    def setBackgroundPalette(self, data):
        if (self.backgroundPalette != data):
            self.backgroundPalette = data
            self.dirty = True

    def getObjectPalette0(self):
        return self.objectPalette0

    def setObjectPalette0(self, data):
        if (self.objectPalette0 != data):
            self.objectPalette0 = data
            self.dirty = True

    def getObjectPalette1(self):
        return self.objectPalette1

    def setObjectPalette1(self, data):
        if (self.objectPalette1 != data):
            self.objectPalette1 = data
            self.dirty = True

    def getWindowY(self):
        return self.windowY

    def setWindowY(self, data):
        self.windowY = data
        
    def getWindowX(self):
        return self.windowX

    def setWindowX(self, data):
        self.windowX = data

    def emulateOAM(self):
        self.stat = (self.stat & 0xFC) | 0x03
        self.cycles += constants.MODE_3_BEGIN_TICKS
        self.transfer = True

    def emulateTransfer(self):
        if self.transfer:
            if (self.display):
                self.drawLine()
            self.stat = (self.stat & 0xFC) | 0x03
            self.cycles += constants.MODE_3_END_TICKS
            self.transfer = False
        else:
            self.stat = (self.stat & 0xFC)
            self.cycles += constants.MODE_0_TICKS
            # H-Blank interrupt
            if ((self.stat & 0x08) != 0 and (self.stat & 0x44) != 0x44):
                self.interrupt.raiseInterrupt(constants.LCD)

    def emulateHBlank(self):
        self.lineY+=1
        if (self.lineY == self.lineYCompare):
            # constants.LYC=LY interrupt
            self.stat |= 0x04
            if ((self.stat & 0x40) != 0):
                self.interrupt.raiseInterrupt(constants.LCD)
        else:
            self.stat &= 0xFB
        if (self.lineY < 144):
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
        elif (self.lineY == 0):
            self.stat = (self.stat & 0xFC) | 0x02
            self.cycles += constants.MODE_2_TICKS
            # constants.OAM interrupt
            if ((self.stat & 0x20) != 0 and (self.stat & 0x44) != 0x44):
                self.interrupt.raiseInterrupt(constants.LCD)
        else:
            if (self.lineY < 153):
                self.lineY+=1
                self.stat = (self.stat & 0xFC) | 0x01
                if (self.lineY == 153):
                    self.cycles += constants.MODE_1_END_TICKS
                else:
                    self.cycles += constants.MODE_1_TICKS
            else:
                self.lineY = self.wlineY = 0
                self.stat = (self.stat & 0xFC) | 0x01
                self.cycles += constants.MODE_1_TICKS - constants.MODE_1_END_TICKS
            if (self.lineY == self.lineYCompare):
                # constants.LYC=LY interrupt
                self.stat |= 0x04
                if ((self.stat & 0x40) != 0):
                    self.interrupt.raiseInterrupt(constants.LCD)
            else:
                self.stat &= 0xFB

    def drawFrame(self):
        self.driver.updateDisplay()

    def clearFrame(self):
        self.clearPixels()
        self.driver.updateDisplay()

    def drawLine(self):
        if ((self.control & 0x01) != 0):
            self.drawBackground()
        else:
            self.drawCleanBackground()
        if ((self.control & 0x20) != 0):
            self.drawWindow()
        if ((self.control & 0x02) != 0):
            self.drawObjects()
        self.drawPixels()

    def drawCleanBackground(self):
        for x in range(0, 8+160+8):
            self.line[x] = 0x00

    def drawBackground(self):
        y = (self.scrollY + self.lineY) & 0xFF
        x = self.scrollX & 0xFF
        tileMap = constants.VRAM_MAP_A
        if (self.control & 0x08) != 0:
            tileMap =  constants.VRAM_MAP_B
        tileData = constants.VRAM_DATA_B
        if (self.control & 0x10) != 0:
            tileData = constants.VRAM_DATA_A
        tileMap += ((y >> 3) << 5) + (x >> 3)
        tileData += (y & 7) << 1
        self.drawTiles(8 - (x & 7), tileMap, tileData)

    def drawWindow(self):
        if (self.lineY >= self.windowY and self.windowX < 167 and self.wlineY < 144):
            tileMap = constants.VRAM_MAP_A
            if (self.control & 0x40) != 0:
                tileMap =  constants.VRAM_MAP_B
            tileData = constants.VRAM_DATA_B
            if (self.control & 0x10) != 0:
                tileData = constants.VRAM_DATA_A
            tileMap += (self.wlineY >> 3) << 5
            tileData += (self.wlineY & 7) << 1
            self.drawTiles(self.windowX + 1, tileMap, tileData)
            self.wlineY+=1

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

            y = self.lineY - y + 16

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
            self.objects[count] = (x << 24) + (count << 20) + (flags << 12) + ((tile << 4) + (y << 1))
            count += 1
            if count >= constants.OBJECTS_PER_LINE:
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
        while (x < 168):
            if (self.control & 0x10) != 0:
                tile = self.vram[tileMap] & 0xFF
            else:
                tile = (self.vram[tileMap] ^ 0x80) & 0xFF
            self.drawTile(x, tileData + (tile << 4))
            tileMap = (tileMap & 0x1FE0) + ((tileMap + 1) & 0x001F)
            x += 8

    def drawTile(self, x, address):
        pattern = (self.vram[address] & 0xFF) + ((self.vram[address + 1] & 0xFF) << 8)
        for i in range(0, 8):
            self.line[x + i] = (pattern >> (7-i)) & 0x0101

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
            self.drawObjectTileXFlipped(x, pattern, mask)
        else:
            self.drawObjectTileNormal(x, pattern, mask)
                    
    def drawObjectTileNormal(self, x, pattern, mask):
            for i in range(0, 7):
                color = (pattern >> (6-i))
                if ((color & 0x0202) != 0):
                    self.line[x + i] |= color | mask
            color = (pattern << 1)
            if ((color & 0x0202) != 0):
                self.line[x + 7] |= color | mask
            
    def drawObjectTileXFlipped(self, x, pattern, mask):
            color = (pattern << 1)
            if ((color & 0x0202) != 0):
                self.line[x + 0] |= color | mask
            for i in range(0, 7):
                color = (pattern >> i)
                if ((color & 0x0202) != 0):
                    self.line[x + i + 1] |= color | mask


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
            self.drawOverlappedObjectTileXFlipped(x, pattern, mask)
        else:
            self.drawOverlappedObjectTileNormal(x, pattern, mask)
            
    def drawOverlappedObjectTileNormal(self, x, pattern, mask):
            for i in range(0,7):
                color = (pattern >> (6-i))
                if ((color & 0x0202) != 0):
                    self.line[x + i] = (self.line[x + i] & 0x0101) | color | mask
            color = (pattern << 1)
            if ((color & 0x0202) != 0):
                self.line[x + 7] = (self.line[x + 7] & 0x0101) | color | mask
                
    def drawOverlappedObjectTileXFlipped(self, x, pattern, mask):
            color = (pattern << 1)
            if ((color & 0x0202) != 0):
                self.line[x + 0] = (self.line[x + 0] & 0x0101) | color | mask
            #TODO maybe a bug in the java implementetation [0,1,2,3,4,6,5]
            for i in range(0,7):
                color = (pattern >> i)
                if ((color & 0x0202) != 0):
                    self.line[x + i + 1] = (self.line[x + i +1] & 0x0101) | color | mask

    def drawPixels(self):
        self.updatePalette()
        pixels = self.driver.getPixels()
        offset = self.lineY * self.driver.getWidth()
        for x in range(8, 168, 4):
            for i in range(0,4):
                pattern = self.line[x + i]
                pixels[offset + i] = self.palette[pattern]
            offset += 4

    def clearPixels(self):
        pixels = self.driver.getPixels()
        for offset in range(0, len(pixels)):
            pixels[offset] = constants.COLOR_MAP[0]

    def updatePalette(self):
        if not self.dirty:
            return
        # bit 4/0 = constants.BG color, bit 5/1 = constants.OBJ color, bit 2 = constants.OBJ palette, bit
        # 3 = constants.OBJ priority
        for pattern in range(0, 64):
            #color
            if ((pattern & 0x22) == 0 or ((pattern & 0x08) != 0 and (pattern & 0x11) != 0)):
                # constants.OBJ behind constants.BG color 1-3
                color = (self.backgroundPalette >> ((((pattern >> 3) & 0x02) + (pattern & 0x01)) << 1)) & 0x03
             # constants.OBJ above constants.BG
            elif ((pattern & 0x04) == 0):
                color = (self.objectPalette0 >> ((((pattern >> 4) & 0x02) + ((pattern >> 1) & 0x01)) << 1)) & 0x03
            else:
                color = (self.objectPalette1 >> ((((pattern >> 4) & 0x02) + ((pattern >> 1) & 0x01)) << 1)) & 0x03
            self.palette[((pattern & 0x30) << 4) + (pattern & 0x0F)] = constants.COLOR_MAP[color]
        self.dirty = False


# ------------------------------------------------------------------------------

class VideoDriver(object):
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.pixels = [0]*width*height
        
    def getWidth(self):
        return self.width
    
    def getHeight(self):
        return selg.height
    
    def getPixels(self):
        return self.pixels
    
    def updateDisplay(self):
        self.resetPixels()
    
        