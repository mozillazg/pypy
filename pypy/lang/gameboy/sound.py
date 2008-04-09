"""
PyBoy GameBoy (TM) Emulator
 
Audio Processor Unit (Sharp LR35902 APU)
"""

from pypy.lang.gameboy import constants
    
class Channel(object):

    # Audio Channel 1 int
    nr10=0
    nr11=0
    nr12=0
    nr13=0
    nr14=0
    audio1Index=0
    audio1Length=0
    audio1Frequency=0
    
    def __init__(self):
        pass
    
class SquareWaveGenerator(Channel):
    pass
    
class VoluntaryWaveGenerator(Channel):
    pass

class NoiseGenerator(Channel):
    pass

    
    
class Sound(object):

    # Audio Channel 1 int
    nr10=0
    nr11=0
    nr12=0
    nr13=0
    nr14=0
    audio1Index=0
    audio1Length=0
    audio1Volume=0
    audio1EnvelopeLength=0
    audio1SweepLength=0
    audio1Frequency=0


    # Audio Channel 2 int
    nr21=0
    nr22=0
    nr23=0
    nr24=0
    audio2Index=0
    audio2Length=0
    audio2Volume=0
    audio2EnvelopeLength=0
    audio2Frequency=0


    # Audio Channel 3 int
    nr30=0
    nr31=0
    nr32=0
    nr33=0
    nr34=0
    audio3Index=0
    audio3Length=0
    audio3Frequency=0
    audio3WavePattern = []# = new byte[16]

    # Audio Channel 4 int
    nr41=0
    nr42=0
    nr43=0
    nr44=0
    audio4Index=0
    audio4Length=0
    audio4Volume=0
    audio4EnvelopeLength=0
    audio4Frequency=0

    # Output Control int
    nr50=0
    nr51=0
    nr52=0

     # Sound DriverSoundDriver
    #driver
    buffer  = []# = new byte[512]
    #int
    #frames
    #cycles

     # Frequency Table
    frequencyTable = []#= new int[2048]
    noiseFreqRatioTable = [] #= new int[8]

     # Noise Tables
    noiseStep7Table = [] #= new int[128 / 32]
    noiseStep15Table = [] #= new int[32768 / 32]

    def __init__(self, soundDriver):
        self.driver = soundDriver
        self.generateFrequencyTables()
        self.generateNoiseTables()
        self.reset()

    def reset(self):
        self.cycles = constants.GAMEBOY_CLOCK / constants.SOUND_CLOCK
        self.frames = 0
        self.audio1Index = self.audio2Index = self.audio3Index = self.audio4Index = 0
        self.write(constants.NR10, 0x80)
        self.write(constants.NR11, 0x3F); #  0xBF
        self.write(constants.NR12, 0x00); #  0xF3
        self.write(constants.NR13, 0xFF)
        self.write(constants.NR14, 0xBF)

        self.write(constants.NR21, 0x3F)
        self.write(constants.NR22, 0x00)
        self.write(constants.NR23, 0xFF)
        self.write(constants.NR24, 0xBF)

        self.write(constants.NR30, 0x7F)
        self.write(constants.NR31, 0xFF)
        self.write(constants.NR32, 0x9F)
        self.write(constants.NR33, 0xFF)
        self.write(constants.NR34, 0xBF)

        self.write(constants.NR41, 0xFF)
        self.write(constants.NR42, 0x00)
        self.write(constants.NR43, 0x00)
        self.write(constants.NR44, 0xBF)

        self.write(constants.NR50, 0x00); #  0x77
        self.write(constants.NR51, 0xF0)
        self.write(constants.NR52, 0xFF); #  0xF0

        for address in range(0xFF30, 0xFF3F):
            write = 0xFF
            if (address & 1) == 0:
                write = 0x00
            self.write(address, write)
            
    def start(self):
        self.driver.start()

    def stop(self):
        self.driver.stop()

    def cycles(self):
        return self.cycles

    def emulate(self, ticks):
        self.cycles -= ticks
        while (self.cycles <= 0):
            self.updateAudio()
            if self.driver.isEnabled():
                self.mixDownAudio()

            self.cycles += constants.GAMEBOY_CLOCK / constants.SOUND_CLOCK
            
    def mixDownAudio(self):
        self.frames += self.driver.getSampleRate()
        length = (self.frames / constants.SOUND_CLOCK) << 1
        self.mixAudio(self.buffer, length)
        self.driver.write(self.buffer, length)
        self.frames %= constants.SOUND_CLOCK
        
    def read(self, address):
        if address==constants.NR10:
            return self.getAudio1Sweep()
        elif address == constants.NR11:
            return self.getAudio1Length()
        elif address == constants.NR12:
            return self.getAudio1Envelope()
        elif address == constants.NR13:
            return self.getAudio1Frequency()
        elif address == constants.NR14:
            return self.getAudio1Playback()

        elif address == constants.NR21:
            return self.getAudio2Length()
        elif address == constants.NR22:
            return self.getAudio2Envelope()
        elif address==constants.NR23:
            return self.getAudio2Frequency()
        elif address==constants.NR24:
            return self.getAudio2Playback()

        elif address==constants.NR30:
            return self.getAudio3Enable()
        elif address==constants.NR31:
            return self.getAudio3Length()
        elif address==constants.NR32:
            return self.getAudio3Level()
        elif address==constants.NR33:
            return self.getAudio4Frequency()
        elif address==constants.NR34:
            return self.getAudio3Playback()

        elif address==constants.NR41:
            return self.getAudio4Length()
        elif address==constants.NR42:
            return self.getAudio4Envelope()
        elif address==constants.NR43:
            return self.getAudio4Polynomial()
        elif address==constants.NR44:
            return self.getAudio4Playback()

        elif address==constants.NR50:
            return self.getOutputLevel()
        elif address==constants.NR51:
            return self.getOutputTerminal()
        elif address==constants.NR52:
            return self.getOutputEnable()

        elif (address >= constants.AUD3WAVERAM and address <= constants.AUD3WAVERAM + 0x3F):
            return self.getAudio3WavePattern(address)
        return 0xFF

    def write(self, address, data):
        if address==constants.NR10:
            self.setAudio1Sweep(data)
        elif address == constants.NR11:
            self.setAudio1Length(data)
        elif address == constants.NR12:
            self.setAudio1Envelope(data)
        elif address == constants.NR13:
            self.setAudio1Frequency(data)
        elif address == constants.NR14:
            self.setAudio1Playback(data)
        
        elif address == constants.NR21:
            self.setAudio2Length(data)
        elif address == constants.NR22:
            self.setAudio2Envelope(data)
        elif address == constants.NR23:
            self.setAudio2Frequency(data)
        elif address == constants.NR24:
            self.setAudio2Playback(data)
        
        elif address == constants.NR30:
            self.setAudio3Enable(data)
        elif address == constants.NR31:
            self.setAudio3Length(data)
        elif address == constants.NR32:
            self.setAudio3Level(data)
        elif address == constants.NR33:
            self.setAudio3Frequency(data)
        elif address == constants.NR34:
            self.setAudio3Playback(data)
        
        elif address == constants.NR41:
            self.setAudio4Length(data)
        elif address == constants.NR42:
            self.setAudio4Envelope(data)
        elif address == constants.NR43:
            self.setAudio4Polynomial(data)
        elif address == constants.NR44:
            self.setAudio4Playback(data)
        
        elif address == constants.NR50:
            self.setOutputLevel(data)
        elif address == constants.NR51:
            self.setOutputTerminal(data)
        elif address == constants.NR52:
            self.setOutputEnable(data)
        
        elif (address >= constants.AUD3WAVERAM and address <= constants.AUD3WAVERAM + 0x3F):
            self.setAudio3WavePattern(address, data)

    def updateAudio(self):
        if (self.nr52 & 0x80) == 0:
            return
        if (self.nr52 & 0x01) != 0:
            self.updateAudio1()
        if (self.nr52 & 0x02) != 0:
            self.updateAudio2()
        if (self.nr52 & 0x04) != 0:
            self.updateAudio3()
        if (self.nr52 & 0x08) != 0:
            self.updateAudio4()

    def mixAudio(self,buffer, length):
        buffer = [0]*length
        if (self.nr52 & 0x80) == 0:
            return
        if (self.nr52 & 0x01) != 0:
            self.mixAudio1(buffer, length)
        if (self.nr52 & 0x02) != 0:
            self.mixAudio2(buffer, length)
        if (self.nr52 & 0x04) != 0:
            self.mixAudio3(buffer, length)
        if (self.nr52 & 0x08) != 0:
            self.mixAudio4(buffer, length)

     # Audio Channel 1
    def getAudio1Sweep(self):
        return self.nr10

    def getAudio1Length(self):
        return self.nr11

    def getAudio1Envelope(self):
        return self.nr12

    def getAudio1Frequency(self):
        return self.nr13

    def getAudio1Playback(self):
        return self.nr14

    def setAudio1Sweep(self, data):
        self.nr10 = data
        self.audio1SweepLength = (constants.SOUND_CLOCK / 128) * ((self.nr10 >> 4) & 0x07)

    def setAudio1Length(self, data):
        self.nr11 = data
        self.audio1Length = (constants.SOUND_CLOCK / 256) * (64 - (self.nr11 & 0x3F))

    def setAudio1Envelope(self, data):
        self.nr12 = data
        if ((self.nr14 & 0x40) != 0):
            return
        if ((self.nr12 >> 4) == 0):
            self.audio1Volume = 0
        elif (self.audio1EnvelopeLength == 0 and (self.nr12 & 0x07) == 0):
            self.audio1Volume = (self.audio1Volume + 1) & 0x0F
        else:
            self.audio1Volume = (self.audio1Volume + 2) & 0x0F

    def setAudio1Frequency(self, data):
        self.nr13 = data
        self.audio1Frequency = self.frequencyTable[self.nr13 + ((self.nr14 & 0x07) << 8)]

    def setAudio1Playback(self, data):
        self.nr14 = data
        self.audio1Frequency = self.frequencyTable[self.nr13
                + ((self.nr14 & 0x07) << 8)]
        if ((self.nr14 & 0x80) != 0):
            self.nr52 |= 0x01
            if ((self.nr14 & 0x40) != 0 and self.audio1Length == 0):
                self.audio1Length = (constants.SOUND_CLOCK / 256) * (64 - (self.nr11 & 0x3F))
            self.audio1SweepLength = (constants.SOUND_CLOCK / 128) * ((self.nr10 >> 4) & 0x07)
            self.audio1Volume = self.nr12 >> 4
            self.audio1EnvelopeLength = (constants.SOUND_CLOCK / 64) * (self.nr12 & 0x07)

    def updateAudio1(self):
        if (self.nr14 & 0x40) != 0 and self.audio1Length > 0:
            self.audio1Length-=1
            if self.audio1Length <= 0:
                self.nr52 &= ~0x01
        if self.audio1EnvelopeLength > 0:
            self.audio1EnvelopeLength-=1
            if (self.audio1EnvelopeLength <= 0):
                if ((self.nr12 & 0x08) != 0):
                    if (self.audio1Volume < 15):
                        self.audio1Volume+=1
                elif (self.audio1Volume > 0):
                    self.audio1Volume-=1
                self.audio1EnvelopeLength += (constants.SOUND_CLOCK / 64) * (self.nr12 & 0x07)
        if (self.audio1SweepLength > 0):
            self.audio1SweepLength-=1
            if (self.audio1SweepLength <= 0):
                sweepSteps = (self.nr10 & 0x07)
                if (sweepSteps != 0):
                    frequency = ((self.nr14 & 0x07) << 8) + self.nr13
                    if ((self.nr10 & 0x08) != 0):
                        frequency -= frequency >> sweepSteps
                    else:
                        frequency += frequency >> sweepSteps
                    if (frequency < 2048):
                        self.audio1Frequency = self.frequencyTable[frequency]
                        self.nr13 = frequency & 0xFF
                        self.nr14 = (self.nr14 & 0xF8) + ((frequency >> 8) & 0x07)
                    else:
                        self.audio1Frequency = 0
                        self.nr52 &= ~0x01
            
                self.audio1SweepLength += (constants.SOUND_CLOCK / 128) * ((self.nr10 >> 4) & 0x07)

    def mixAudio1(self, buffer, length):
        wavePattern = 0x18
        if (self.nr11 & 0xC0) == 0x00:
            wavePattern = 0x04
        elif (self.nr11 & 0xC0) == 0x40:
            wavePattern = 0x08
        elif (self.nr11 & 0xC0) == 0x80:
            wavePattern = 0x10
        wavePattern << 22
        for index in range(0, length, 3):
            self.audio1Index += self.audio1Frequency
            if ((self.audio1Index & (0x1F << 22)) >= wavePattern):
                if ((self.nr51 & 0x10) != 0):
                    buffer[index + 0] -= self.audio1Volume
                if ((self.nr51 & 0x01) != 0):
                    buffer[index + 1] -= self.audio1Volume
            else:
                if ((self.nr51 & 0x10) != 0):
                    buffer[index + 0] += self.audio1Volume
                if ((self.nr51 & 0x01) != 0):
                    buffer[index + 1] += self.audio1Volume
        
     # Audio Channel 2
    def getAudio2Length(self):
        return self.nr21

    def getAudio2Envelope(self):
        return self.nr22

    def getAudio2Frequency(self):
        return self.nr23

    def getAudio2Playback(self):
        return self.nr24

    def setAudio2Length(self, data):
        self.nr21 = data
        self.audio2Length = (constants.SOUND_CLOCK / 256) * (64 - (self.nr21 & 0x3F))

    def setAudio2Envelope(self, data):
        self.nr22 = data
        if ((self.nr24 & 0x40) == 0):
            if ((self.nr22 >> 4) == 0):
                self.audio2Volume = 0
            elif (self.audio2EnvelopeLength == 0 and (self.nr22 & 0x07) == 0):
                self.audio2Volume = (self.audio2Volume + 1) & 0x0F
            else:
                self.audio2Volume = (self.audio2Volume + 2) & 0x0F

    def setAudio2Frequency(self, data):
        self.nr23 = data
        self.audio2Frequency = self.frequencyTable[self.nr23\
                + ((self.nr24 & 0x07) << 8)]

    def setAudio2Playback(self, data):
        self.nr24 = data
        self.audio2Frequency = self.frequencyTable[self.nr23\
                + ((self.nr24 & 0x07) << 8)]
        if ((self.nr24 & 0x80) != 0):
            self.nr52 |= 0x02
            if ((self.nr24 & 0x40) != 0 and self.audio2Length == 0):
                self.audio2Length = (constants.SOUND_CLOCK / 256) * (64 - (self.nr21 & 0x3F))
            self.audio2Volume = self.nr22 >> 4
            self.audio2EnvelopeLength = (constants.SOUND_CLOCK / 64) * (self.nr22 & 0x07)
    
    def updateAudio2(self):
        if ((self.nr24 & 0x40) != 0 and self.audio2Length > 0):
            self.audio2Length-=1
            if (self.audio2Length <= 0):
                self.nr52 &= ~0x02
        if (self.audio2EnvelopeLength > 0):
            self.audio2EnvelopeLength-=1

            if (self.audio2EnvelopeLength <= 0):
                if ((self.nr22 & 0x08) != 0):
                    if (self.audio2Volume < 15):
                        self.audio2Volume+=1
                elif (self.audio2Volume > 0):
                    self.audio2Volume-=1
                self.audio2EnvelopeLength += (constants.SOUND_CLOCK / 64) * (self.nr22 & 0x07)
        
    def mixAudio2(self, buffer, length):
        wavePattern = 0x18
        if (self.nr21 & 0xC0) == 0x00:
            wavePattern = 0x04
        elif (self.nr21 & 0xC0) == 0x40:
            wavePattern = 0x08
        elif (self.nr21 & 0xC0) == 0x80:
            wavePattern = 0x10
        wavePattern << 22
        for index in range(0, length):
            self.audio2Index += self.audio2Frequency
            if ((self.audio2Index & (0x1F << 22)) >= wavePattern):
                if ((self.nr51 & 0x20) != 0):
                    buffer[index + 0] -= self.audio2Volume
                if ((self.nr51 & 0x02) != 0):
                    buffer[index + 1] -= self.audio2Volume
            else:
                if ((self.nr51 & 0x20) != 0):
                    buffer[index + 0] += self.audio2Volume
                if ((self.nr51 & 0x02) != 0):
                    buffer[index + 1] += self.audio2Volume

     # Audio Channel 3
    def getAudio3Enable(self):
        return self.nr30

    def getAudio3Length(self):
        return self.nr31

    def getAudio3Level(self):
        return self.nr32

    def getAudio4Frequency(self):
        return self.nr33

    def getAudio3Playback(self):
        return self.nr34

    def setAudio3Enable(self, data):
        self.nr30 = data & 0x80
        if ((self.nr30 & 0x80) == 0):
            self.nr52 &= ~0x04

    def setAudio3Length(self, data):
        self.nr31 = data
        self.audio3Length = (constants.SOUND_CLOCK / 256) * (256 - self.nr31)

    def setAudio3Level(self, data):
        self.nr32 = data

    def setAudio3Frequency(self, data):
        self.nr33 = data
        self.audio3Frequency = self.frequencyTable[((self.nr34 & 0x07) << 8) + self.nr33] >> 1

    def setAudio3Playback(self, data):
        self.nr34 = data
        self.audio3Frequency = self.frequencyTable[((self.nr34 & 0x07) << 8) + self.nr33] >> 1
        if ((self.nr34 & 0x80) != 0 and (self.nr30 & 0x80) != 0):
            self.nr52 |= 0x04
            if ((self.nr34 & 0x40) != 0 and self.audio3Length == 0):
                self.audio3Length = (constants.SOUND_CLOCK / 256) * (256 - self.nr31)
    
    def setAudio3WavePattern(self, address, data):
        self.audio3WavePattern[address & 0x0F] = data

    def getAudio3WavePattern(self, address):
        return self.audio3WavePattern[address & 0x0F] & 0xFF

    def updateAudio3(self):
        if ((self.nr34 & 0x40) != 0 and self.audio3Length > 0):
            self.audio3Length-=1
            if (self.audio3Length <= 0):
                self.nr52 &= ~0x04

    def mixAudio3(self, buffer, length):
        wavePattern = 2
        if (self.nr32 & 0x60) == 0x00:
            wavePattern = 8
        elif (self.nr32 & 0x60) == 0x40:
            wavePattern = 0
        elif (self.nr32 & 0x60) == 0x80:
            wavePattern = 1

        for index in range(0, length, 2):
            self.audio3Index += self.audio3Frequency
            sample = self.audio3WavePattern[(self.audio3Index >> 23) & 0x0F]
            if ((self.audio3Index & (1 << 22)) != 0):
                sample = (sample >> 0) & 0x0F
            else:
                sample = (sample >> 4) & 0x0F

            sample = ((sample - 8) << 1) >> level

            if ((self.nr51 & 0x40) != 0):
                buffer[index + 0] += sample
            if ((self.nr51 & 0x04) != 0):
                buffer[index + 1] += sample
    
     # Audio Channel 4
    def getAudio4Length(self):
        return self.nr41

    def getAudio4Envelope(self):
        return self.nr42

    def getAudio4Polynomial(self):
        return self.nr43

    def getAudio4Playback(self):
        return self.nr44

    def setAudio4Length(self, data):
        self.nr41 = data
        self.audio4Length = (constants.SOUND_CLOCK / 256) * (64 - (self.nr41 & 0x3F))

    def setAudio4Envelope(self, data):
        self.nr42 = data
        if ((self.nr44 & 0x40) == 0):
            if ((self.nr42 >> 4) == 0):
                self.audio4Volume = 0
            elif (self.audio4EnvelopeLength == 0 and (self.nr42 & 0x07) == 0):
                self.audio4Volume = (self.audio4Volume + 1) & 0x0F
            else:
                self.audio4Volume = (self.audio4Volume + 2) & 0x0F

    def setAudio4Polynomial(self, data):
        self.nr43 = data
        if ((self.nr43 >> 4) <= 12):
            self.audio4Frequency = self.noiseFreqRatioTable[self.nr43 & 0x07] >> ((self.nr43 >> 4) + 1)
        else:
            self.audio4Frequency = 0

    def setAudio4Playback(self, data):
        self.nr44 = data
        if ((self.nr44 & 0x80) != 0):
            self.nr52 |= 0x08
            if ((self.nr44 & 0x40) != 0 and self.audio4Length == 0):
                self.audio4Length = (constants.SOUND_CLOCK / 256) * (64 - (self.nr41 & 0x3F))
            self.audio4Volume = self.nr42 >> 4
            self.audio4EnvelopeLength = (constants.SOUND_CLOCK / 64) * (self.nr42 & 0x07)
            self.audio4Index = 0

    def updateAudio4(self):
        if ((self.nr44 & 0x40) != 0 and self.audio4Length > 0):
            self.audio4Length-=1
            if (self.audio4Length <= 0):
                self.nr52 &= ~0x08
        if (self.audio4EnvelopeLength > 0):
            self.audio4EnvelopeLength-=1
            if (self.audio4EnvelopeLength <= 0):
                if ((self.nr42 & 0x08) != 0):
                    if (self.audio4Volume < 15):
                        self.audio4Volume+=1
                elif (self.audio4Volume > 0):
                    self.audio4Volume-=1
                self.audio4EnvelopeLength += (constants.SOUND_CLOCK / 64) * (self.nr42 & 0x07)
    
    def mixAudio4(self, buffer, length):
        for index in range(0, length, 2):
            self.audio4Index += self.audio4Frequency
            polynomial
            if ((self.nr43 & 0x08) != 0):
                #  7 steps
                self.audio4Index &= 0x7FFFFF
                polynomial = self.noiseStep7Table[self.audio4Index >> 21] >> ((self.audio4Index >> 16) & 31)
            else:
                #  15 steps
                self.audio4Index &= 0x7FFFFFFF
                polynomial = self.noiseStep15Table[self.audio4Index >> 21] >> ((self.audio4Index >> 16) & 31)
            if ((polynomial & 1) != 0):
                if ((self.nr51 & 0x80) != 0):
                    buffer[index + 0] -= self.audio4Volume
                if ((self.nr51 & 0x08) != 0):
                    buffer[index + 1] -= self.audio4Volume
            else:
                if ((self.nr51 & 0x80) != 0):
                    buffer[index + 0] += self.audio4Volume
                if ((self.nr51 & 0x08) != 0):
                    buffer[index + 1] += self.audio4Volume

     # Output Control
    def getOutputLevel(self):
        return self.nr50

    def getOutputTerminal(self):
        return self.nr51

    def getOutputEnable(self):
        return self.nr52

    def setOutputLevel(self, data):
        self.nr50 = data

    def setOutputTerminal(self, data):
        self.nr51 = data

    def setOutputEnable(self, data):
        self.nr52 = (self.nr52 & 0x7F) | (data & 0x80)
        if ((self.nr52 & 0x80) == 0x00):
            self.nr52 &= 0xF0

     # Frequency Table Generation
    def generateFrequencyTables(self):
        sampleRate = self.driver.getSampleRate()
         # frequency = (4194304 / 32) / (2048 - period) Hz
        for period in range(0, 2048):
            skip = (((constants.GAMEBOY_CLOCK << 10) / sampleRate) << (22 - 8)) / (2048 - period)
            if (skip >= (32 << 22)):
                self.frequencyTable[period] = 0
            else:
                self.frequencyTable[period] = skip
         # Polynomial Noise Frequency Ratios
         # 4194304 Hz * 1/2^3 * 2 4194304 Hz * 1/2^3 * 1 4194304 Hz * 1/2^3 *
         # 1/2 4194304 Hz * 1/2^3 * 1/3 4194304 Hz * 1/2^3 * 1/4 4194304 Hz *
         # 1/2^3 * 1/5 4194304 Hz * 1/2^3 * 1/6 4194304 Hz * 1/2^3 * 1/7
        for ratio in range(0, 8):
            divider = 1
            if ratio != 0:
                divider = 2 * ratio
            self.noiseFreqRatioTable[ratio] = (constants.GAMEBOY_CLOCK / divider) * ((1 << 16) / sampleRate)

     # Noise Generation
    def generateNoiseTables(self):
        polynomial = 0x7F
        #  7 steps
        for  index in range(0, 0x7F):
            polynomial = (((polynomial << 6) ^ (polynomial << 5)) & 0x40) | (polynomial >> 1)
            if ((index & 31) == 0):
                self.noiseStep7Table[index >> 5] = 0
            self.noiseStep7Table[index >> 5] |= (polynomial & 1) << (index & 31)
        #  15 steps&
        polynomial = 0x7FFF
        for index in range(0, 0x7FFF):
            polynomial = (((polynomial << 14) ^ (polynomial << 13)) & 0x4000) | (polynomial >> 1)
            if ((index & 31) == 0):
                self.noiseStep15Table[index >> 5] = 0
            self.noiseStep15Table[index >> 5] |= (polynomial & 1) << (index & 31)
            
            
# SOUND DRIVER -----------------------------------------------------------------

class SoundDriver(object):
    
    def __init__(self):
        self.enabled = True
    
    def isEnabled(self):
        return self.enabled
    
    def getSampleRate(self):
        self.sampleRate
    
    def getChannels(self):
        return self.channelCount
    
    def getBitsPerSample(self):
        return self.bitsPerSample
    
    def start(self):
        pass
        
    def stop(self):
        pass
    
    def write(self, buffer, length):
        pass
