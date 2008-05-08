"""
PyBoy GameBoy (TM) Emulator
 
Audio Processor Unit (Sharp LR35902 APU)
"""

from pypy.lang.gameboy import constants
    
class Channel(object):

    audioIndex = 0
    audioLength = 0
    audioFrequency = 0
    
    def __init__(self, sampleRate, frequencyTable):
        self.sampleRate = sampleRate
        self.frequencyTable = frequencyTable
        self.audioLength=0
        self.audioEnvelope=0
        self.audioFrequency=0
        self.audioPlayback=0
        self.nr0 = 0
        self.nr1 = 0
        self.nr2 = 0
        self.nr3 = 0
        self.nr4 = 0
        self.audioIndex = 0
        self.audioLength = 0
        self.audioFrequency = 0
        self.enabled = False
        
    def reset(self):
        self.audioIndex = 0
    
    def get_audio_length(self):
        return self.audioLength

    def get_audio_envelope(self):
        return self.audioEnvelope

    def get_audio_frequency(self):
        return self.audioFrequency

    def get_audio_playback(self):
        return self.audioPlayback
        

    
# ------------------------------------------------------------------------------

#SquareWaveGenerator
class Channel1(Channel):
        # Audio Channel 1 int
    def __init__(self, sampleRate, frequencyTable):
        Channel.__init__(self, sampleRate, frequencyTable)
        self.audioSweep=0
        self.audio1Index=0
        self.audio1Length=0
        self.audioVolume=0
        self.audio1EnvelopeLength=0
        self.audioSweepLength=0
        self.audio1Frequency=0
    
     # Audio Channel 1
    def get_audio_sweep(self):
        return self.audioSweep

    def set_audio_sweep(self, data):
        self.audioSweep = data
        self.audioSweepLength = (constants.SOUND_CLOCK / 128) * \
                                ((self.audioSweep >> 4) & 0x07)

    def set_audio_length(self, data):
        self.audioLength = data
        self.audio1Length = (constants.SOUND_CLOCK / 256) * \
                            (64 - (self.audioLength & 0x3F))

    def set_audio_envelope(self, data):
        self.audioEnvelope = data
        if (self.audioPlayback & 0x40) != 0:
            return
        if (self.audioEnvelope >> 4) == 0:
            self.audioVolume = 0
        elif self.audio1EnvelopeLength == 0 and \
             (self.audioEnvelope & 0x07) == 0:
            self.audioVolume = (self.audioVolume + 1) & 0x0F
        else:
            self.audioVolume = (self.audioVolume + 2) & 0x0F

    def set_audio_frequency(self, data):
        self.audioFrequency = data
        index = self.audioFrequency + ((self.audioPlayback & 0x07) << 8)
        self.audio1Frequency = self.frequencyTable[index]

    def set_audio_playback(self, data):
        self.audioPlayback = data
        self.audio1Frequency = self.frequencyTable[self.audioFrequency
                + ((self.audioPlayback & 0x07) << 8)]
        if (self.audioPlayback & 0x80) != 0:
            self.enabled = True
            if (self.audioPlayback & 0x40) != 0 and self.audio1Length == 0:
                self.audio1Length = (constants.SOUND_CLOCK / 256) * \
                                    (64 - (self.audioLength & 0x3F))
            self.audioSweepLength = (constants.SOUND_CLOCK / 128) * \
                                    ((self.audioSweep >> 4) & 0x07)
            self.audioVolume = self.audioEnvelope >> 4
            self.audio1EnvelopeLength = (constants.SOUND_CLOCK / 64) * \
                                        (self.audioEnvelope & 0x07)

    def update_audio(self):
        if (self.audioPlayback & 0x40) != 0 and self.audio1Length > 0:
            self.audio1Length-=1
            if self.audio1Length <= 0:
                self.enabled = False
        if self.audio1EnvelopeLength > 0:
            self.audio1EnvelopeLength-=1
            if self.audio1EnvelopeLength <= 0:
                if (self.audioEnvelope & 0x08) != 0:
                    if (self.audioVolume < 15):
                        self.audioVolume+=1
                elif self.audioVolume > 0:
                    self.audioVolume-=1
                self.audio1EnvelopeLength += (constants.SOUND_CLOCK / 64) * \
                                             (self.audioEnvelope & 0x07)
        if self.audioSweepLength > 0:
            self.audioSweepLength-=1
            if self.audioSweepLength <= 0:
                sweepSteps = (self.audioSweep & 0x07)
                if sweepSteps != 0:
                    frequency = ((self.audioPlayback & 0x07) << 8) + \
                                self.audioFrequency
                    if (self.audioSweep & 0x08) != 0:
                        frequency -= frequency >> sweepSteps
                    else:
                        frequency += frequency >> sweepSteps
                    if frequency < 2048:
                        self.audio1Frequency = self.frequencyTable[frequency]
                        self.audioFrequency = frequency & 0xFF
                        self.audioPlayback = (self.audioPlayback & 0xF8) + \
                                             ((frequency >> 8) & 0x07)
                    else:
                        self.audio1Frequency = 0
                        self.outputEnable &= ~0x01
                self.audioSweepLength += (constants.SOUND_CLOCK / 128) * \
                                         ((self.audioSweep >> 4) & 0x07)

    def mix_audio(self, buffer, length):
        wavePattern = 0x18
        if (self.audioLength & 0xC0) == 0x00:
            wavePattern = 0x04
        elif (self.audioLength & 0xC0) == 0x40:
            wavePattern = 0x08
        elif (self.audioLength & 0xC0) == 0x80:
            wavePattern = 0x10
        wavePattern << 22
        for index in range(0, length, 3):
            self.audio1Index += self.audio1Frequency
            if (self.audio1Index & (0x1F << 22)) >= wavePattern:
                if (self.outputTerminal & 0x10) != 0:
                    buffer[index + 0] -= self.audioVolume
                if (self.outputTerminal & 0x01) != 0:
                    buffer[index + 1] -= self.audioVolume
            else:
                if (self.outputTerminal & 0x10) != 0:
                    buffer[index + 0] += self.audioVolume
                if (self.outputTerminal & 0x01) != 0:
                    buffer[index + 1] += self.audioVolume
                    
    

#SquareWaveGenerator
class Channel2(Channel):

    def __init__(self, sampleRate, frequencyTable):
        Channel.__init__(self, sampleRate, frequencyTable)
        self.audio2Index=0
        self.audio2Length=0
        self.audioVolume=0
        self.audio2EnvelopeLength=0
        self.audio2Frequency=0
      
    # Audio Channel 2
    def set_audio_length(self, data):
        self.audioLength = data
        self.audio2Length = (constants.SOUND_CLOCK / 256) * \
                            (64 - (self.audioLength & 0x3F))

    def set_audio_envelope(self, data):
        self.audioEnvelope = data
        if (self.audioPlayback & 0x40) == 0:
            if (self.audioEnvelope >> 4) == 0:
                self.audioVolume = 0
            elif self.audio2EnvelopeLength == 0 and \
                 (self.audioEnvelope & 0x07) == 0:
                self.audioVolume = (self.audioVolume + 1) & 0x0F
            else:
                self.audioVolume = (self.audioVolume + 2) & 0x0F

    def set_audio_frequency(self, data):
        self.audioFrequency = data
        self.audio2Frequency = self.frequencyTable[self.audioFrequency\
                + ((self.audioPlayback & 0x07) << 8)]

    def set_audio_playback(self, data):
        self.audioPlayback = data
        self.audio2Frequency = self.frequencyTable[self.audioFrequency\
                + ((self.audioPlayback & 0x07) << 8)]
        if (self.audioPlayback & 0x80) != 0:
            self.enabled = True
            if (self.audioPlayback & 0x40) != 0 and self.audio2Length == 0:
                self.audio2Length = (constants.SOUND_CLOCK / 256) * \
                                    (64 - (self.audioLength & 0x3F))
            self.audioVolume = self.audioEnvelope >> 4
            self.audio2EnvelopeLength = (constants.SOUND_CLOCK / 64) * \
                                        (self.audioEnvelope & 0x07)
    
    def update_audio(self):
        if (self.audioPlayback & 0x40) != 0 and self.audio2Length > 0:
            self.audio2Length-=1
            if self.audio2Length <= 0:
                self.enabled = False
        if self.audio2EnvelopeLength > 0:
            self.audio2EnvelopeLength-=1
            if self.audio2EnvelopeLength <= 0:
                if (self.audioEnvelope & 0x08) != 0:
                    if self.audioVolume < 15:
                        self.audioVolume+=1
                elif self.audioVolume > 0:
                    self.audioVolume-=1
                self.audio2EnvelopeLength += (constants.SOUND_CLOCK / 64) *\
                                             (self.audioEnvelope & 0x07)
        
    def mix_audio(self, buffer, length):
        wavePattern = 0x18
        if (self.audioLength & 0xC0) == 0x00:
            wavePattern = 0x04
        elif (self.audioLength & 0xC0) == 0x40:
            wavePattern = 0x08
        elif (self.audioLength & 0xC0) == 0x80:
            wavePattern = 0x10
        wavePattern << 22
        for index in range(0, length):
            self.audio2Index += self.audio2Frequency
            if ((self.audio2Index & (0x1F << 22)) >= wavePattern):
                if ((self.outputTerminal & 0x20) != 0):
                    buffer[index + 0] -= self.audioVolume
                if ((self.outputTerminal & 0x02) != 0):
                    buffer[index + 1] -= self.audioVolume
            else:
                if ((self.outputTerminal & 0x20) != 0):
                    buffer[index + 0] += self.audioVolume
                if ((self.outputTerminal & 0x02) != 0):
                    buffer[index + 1] += self.audioVolume



    
    
#SquareWaveGenerator
class Channel3(Channel):  

    def __init__(self, sampleRate, frequencyTable):
        Channel.__init__(self, sampleRate, frequencyTable)
        self.audioEnable=0
        self.audioLevel=0
        self.audio3Index=0
        self.audio3Length=0
        self.audio3Frequency=0
        self.audioWavePattern = [0]*16
    
    def get_audio_enable(self):
        return self.audioEnable

    def get_audio_level(self):
        return self.audioLevel
    
    #FIXME strange number here
    def get_audio_4_frequency(self):
        return self.audioFrequency

    def set_audio_enable(self, data):
        self.audioEnable = data & 0x80
        if (self.audioEnable & 0x80) == 0:
            self.enabled = False

    def set_audio_length(self, data):
        self.audioLength = data
        self.audio3Length = (constants.SOUND_CLOCK / 256) * \
                            (256 - self.audioLength)

    def set_audio_level(self, data):
        self.audioLevel = data

    def set_audio_frequency(self, data):
        self.audioFrequency = data
        index = ((self.audioPlayback & 0x07) << 8) + self.audioFrequency
        self.audio3Frequency = self.frequencyTable[index] >> 1

    def set_audio_playback(self, data):
        self.audioPlayback = data
        index = ((self.audioPlayback & 0x07) << 8) + self.audioFrequency
        self.audio3Frequency = self.frequencyTable[index] >> 1
        if (self.audioPlayback & 0x80) != 0 and (self.audioEnable & 0x80) != 0:
            self.enabled = True
            if (self.audioPlayback & 0x40) != 0 and self.audio3Length == 0:
                self.audio3Length = (constants.SOUND_CLOCK / 256) *\
                                    (256 - self.audioLength)
    
    def set_audio_wave_pattern(self, address, data):
        self.audioWavePattern[address & 0x0F] = data

    def get_audio_wave_pattern(self, address):
        return self.audioWavePattern[address & 0x0F] & 0xFF

    def update_audio(self):
        if (self.audioPlayback & 0x40) != 0 and self.audio3Length > 0:
            self.audio3Length-=1
            if self.audio3Length <= 0:
                self.outputEnable &= ~0x04

    def mix_audio(self, buffer, length):
        wavePattern = 2
        if (self.audioLevel & 0x60) == 0x00:
            wavePattern = 8
        elif (self.audioLevel & 0x60) == 0x40:
            wavePattern = 0
        elif (self.audioLevel & 0x60) == 0x80:
            wavePattern = 1
        for index in range(0, length, 2):
            self.audio3Index += self.audio3Frequency
            sample = self.audioWavePattern[(self.audio3Index >> 23) & 0x0F]
            if ((self.audio3Index & (1 << 22)) != 0):
                sample = (sample >> 0) & 0x0F
            else:
                sample = (sample >> 4) & 0x0F

            sample = ((sample - 8) << 1) >> level

            if (self.outputTerminal & 0x40) != 0:
                buffer[index + 0] += sample
            if (self.outputTerminal & 0x04) != 0:
                buffer[index + 1] += sample
    
    
    
class NoiseGenerator(Channel):
        
    def __init__(self, sampleRate, frequencyTable):
        Channel.__init__(self, sampleRate, frequencyTable)
            # Audio Channel 4 int
        self.audioLength=0
        self.audioPolynomial=0
        self.audio4Index=0
        self.audio4Length=0
        self.audioVolume=0
        self.audio4EnvelopeLength=0
        self.audio4Frequency=0
        
        self.generate_noise_frequency_ratio_table()
        self.generate_noise_tables()
    
    def generate_noise_frequency_ratio_table(self):
         # Polynomial Noise Frequency Ratios
         # 4194304 Hz * 1/2^3 * 2 4194304 Hz * 1/2^3 * 1 4194304 Hz * 1/2^3 *
         # 1/2 4194304 Hz * 1/2^3 * 1/3 4194304 Hz * 1/2^3 * 1/4 4194304 Hz *
         # 1/2^3 * 1/5 4194304 Hz * 1/2^3 * 1/6 4194304 Hz * 1/2^3 * 1/7
        self.noiseFreqRatioTable = [0] * 8
        sampleFactor = ((1 << 16) / self.sampleRate)
        for ratio in range(0, 8):
            divider = 1
            if ratio != 0:
                divider = 2 * ratio
            self.noiseFreqRatioTable[ratio] = (constants.GAMEBOY_CLOCK / \
                                             divider) *sampleFactor

    def generate_noise_tables(self):
        self.create_7_step_noise_table()
        self.create_15_step_noise_table()
        
    def create_7_step_noise_table(self):
         # Noise Tables
        self. noiseStep7Table = [0]*4
        polynomial = 0x7F
        #  7 steps
        for  index in range(0, 0x7F):
            polynomial = (((polynomial << 6) ^ (polynomial << 5)) & 0x40) | \
                         (polynomial >> 1)
            if (index & 31) == 0:
                self.noiseStep7Table[index >> 5] = 0
            self.noiseStep7Table[index >> 5] |= (polynomial & 1) << \
                                                (index & 31)
            
    def create_15_step_noise_table(self):
        #  15 steps&
        self.noiseStep15Table = [0]*1024
        polynomial = 0x7FFF
        for index in range(0, 0x7FFF):
            polynomial = (((polynomial << 14) ^ (polynomial << 13)) & \
                         0x4000) | (polynomial >> 1)
            if (index & 31) == 0:
                self.noiseStep15Table[index >> 5] = 0
            self.noiseStep15Table[index >> 5] |= (polynomial & 1) << \
                                                 (index & 31)
    
     # Audio Channel 4
    def get_audio_length(self):
        return self.audioLength

    def get_audio_polynomial(self):
        return self.audioPolynomial

    def get_audio_playback(self):
        return self.audioPlayback

    def set_audio_length(self, data):
        self.audioLength = data
        self.audio4Length = (constants.SOUND_CLOCK / 256) * \
                            (64 - (self.audioLength & 0x3F))

    def set_audio_envelope(self, data):
        self.audioEnvelope = data
        if (self.audioPlayback & 0x40) == 0:
            if (self.audioEnvelope >> 4) == 0:
                self.audioVolume = 0
            elif self.audio4EnvelopeLength == 0 and \
                 (self.audioEnvelope & 0x07) == 0:
                self.audioVolume = (self.audioVolume + 1) & 0x0F
            else:
                self.audioVolume = (self.audioVolume + 2) & 0x0F

    def set_audio_polynomial(self, data):
        self.audioPolynomial = data
        if (self.audioPolynomial >> 4) <= 12:
            freq = self.noiseFreqRatioTable[self.audioPolynomial & 0x07]
            self.audio4Frequency = freq >> ((self.audioPolynomial >> 4) + 1)
        else:
            self.audio4Frequency = 0

    def set_audio_playback(self, data):
        self.audioPlayback = data
        if (self.audioPlayback & 0x80) != 0:
            self.enabled = True
            if (self.audioPlayback & 0x40) != 0 and self.audio4Length == 0:
                self.audio4Length = (constants.SOUND_CLOCK / 256) * \
                                    (64 - (self.audioLength & 0x3F))
            self.audioVolume = self.audioEnvelope >> 4
            self.audio4EnvelopeLength = (constants.SOUND_CLOCK / 64) * \
                                        (self.audioEnvelope & 0x07)
            self.audio4Index = 0

    def update_audio(self):
        if (self.audioPlayback & 0x40) != 0 and self.audio4Length > 0:
            self.audio4Length-=1
            if self.audio4Length <= 0:
                self.outputEnable &= ~0x08
        if self.audio4EnvelopeLength > 0:
            self.audio4EnvelopeLength-=1
            if self.audio4EnvelopeLength <= 0:
                if (self.audioEnvelope & 0x08) != 0:
                    if self.audioVolume < 15:
                        self.audioVolume+=1
                elif self.audioVolume > 0:
                    self.audioVolume-=1
                self.audio4EnvelopeLength += (constants.SOUND_CLOCK / 64) *\
                                             (self.audioEnvelope & 0x07)
    
    def mix_audio(self, buffer, length):
        for index in range(0, length, 2):
            self.audio4Index += self.audio4Frequency
            polynomial
            if (self.audioPolynomial & 0x08) != 0:
                #  7 steps
                self.audio4Index &= 0x7FFFFF
                polynomial = self.noiseStep7Table[self.audio4Index >> 21] >>\
                             ((self.audio4Index >> 16) & 31)
            else:
                #  15 steps
                self.audio4Index &= 0x7FFFFFFF
                polynomial = self.noiseStep15Table[self.audio4Index >> 21] >> \
                             ((self.audio4Index >> 16) & 31)
            if (polynomial & 1) != 0:
                if (self.outputTerminal & 0x80) != 0:
                    buffer[index + 0] -= self.audioVolume
                if (self.outputTerminal & 0x08) != 0:
                    buffer[index + 1] -= self.audioVolume
            else:
                if (self.outputTerminal & 0x80) != 0:
                    buffer[index + 0] += self.audioVolume
                if (self.outputTerminal & 0x08) != 0:
                    buffer[index + 1] += self.audioVolume

    
    
# ------------------------------------------------------------------------------

        
class Sound(object):

    def __init__(self, soundDriver):
        self.buffer  = [0]*512
        self.outputLevel=0
        self.outputTerminal=0
        self.outputEnable=0
        
        self.driver = soundDriver
        self.sampleRate =  self.driver.get_sample_rate()
        
        self.generate_frequency_table()
        self.create_audio_channels()
        
        self.reset()
        
    def create_audio_channels(self):
        self.channel1 = Channel1(self.sampleRate, self.frequencyTable)
        self.channel2 = Channel2(self.sampleRate, self.frequencyTable)
        self.channel3 = Channel3(self.sampleRate, self.frequencyTable)
        self.channel4 = NoiseGenerator(self.sampleRate, self.frequencyTable)
        
        
    def generate_frequency_table(self):
        self.frequencyTable = [0] * 2048
         # frequency = (4194304 / 32) / (2048 - period) Hz
        for period in range(0, 2048):
            skip = (((constants.GAMEBOY_CLOCK << 10) / \
                   self.sampleRate) << 16) / (2048 - period)
            if skip >= (32 << 22):
                self.frequencyTable[period] = 0
            else:
                self.frequencyTable[period] = skip

    def reset(self):
        self.cycles = constants.GAMEBOY_CLOCK / constants.SOUND_CLOCK
        self.frames = 0
        self.channel1.reset()
        self.channel2.reset()
        self.channel3.reset()
        self.channel4.reset()
        
        self.channel1.audioIndex = 0
        self.channel2.audioIndex = 0
        self.channel3.audioIndex = 0
        self.channel4.audioIndex = 0
        
        self.write(constants.NR10, 0x80)
        self.write(constants.NR11, 0x3F) #  0xBF
        self.write(constants.NR12, 0x00) #  0xF3
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

        self.write(constants.NR50, 0x00) #  0x77
        self.write(constants.NR51, 0xF0)
        self.write(constants.NR52, 0xFF) #  0xF0

        for address in range(0xFF30, 0xFF3F):
            write = 0xFF
            if (address & 1) == 0:
                write = 0x00
            self.write(address, write)
            
    def start(self):
        self.driver.start()

    def stop(self):
        self.driver.stop()

    def get_cycles(self):
        return self.cycles

    def emulate(self, ticks):
        self.cycles -= ticks
        while (self.cycles <= 0):
            self.update_audio()
            if self.driver.isEnabled():
                self.mix_down_audio()
            self.cycles += constants.GAMEBOY_CLOCK / constants.SOUND_CLOCK
            
    def mix_down_audio(self):
        self.frames += self.driver.get_sample_rate()
        length = (self.frames / constants.SOUND_CLOCK) << 1
        self.mix_audio(self.buffer, length)
        self.driver.write(self.buffer, length)
        self.frames %= constants.SOUND_CLOCK
        
    def read(self, address):
        if address==constants.NR10:
            return self.channel1.get_audio_sweep()
        elif address == constants.NR11:
            return self.channel1.get_audio_length()
        elif address == constants.NR12:
            return self.channel1.get_audio_envelope()
        elif address == constants.NR13:
            return self.channel1.get_audio_frequency()
        elif address == constants.NR14:
            return self.channel1.get_audio_playback()

        elif address == constants.NR21:
            return self.channel2.get_audio_length()
        elif address == constants.NR22:
            return self.channel2.get_audio_envelope()
        elif address==constants.NR23:
            return self.channel2.get_audio_frequency()
        elif address==constants.NR24:
            return self.channel2.get_audio_playback()

        elif address==constants.NR30:
            return self.channel3.get_audio_enable()
        elif address==constants.NR31:
            return self.channel3.get_audio_length()
        elif address==constants.NR32:
            return self.channel3.get_audio_level()
        elif address==constants.NR33:
            return self.channel4.get_audio_frequency()
        elif address==constants.NR34:
            return self.channel3.get_audio_playback()

        elif address==constants.NR41:
            return self.channel4.get_audio_length()
        elif address==constants.NR42:
            return self.channel4.get_audio_envelope()
        elif address==constants.NR43:
            return self.channel4.get_audio_polynomial()
        elif address==constants.NR44:
            return self.channel4.get_audio_playback()

        elif address==constants.NR50:
            return self.get_output_level()
        elif address==constants.NR51:
            return self.get_output_terminal()
        elif address==constants.NR52:
            return self.get_output_enable()

        elif address >= constants.AUD3WAVERAM and \
             address <= constants.AUD3WAVERAM + 0x3F:
            return self.channel3.get_audio_wave_pattern(address)
        return 0xFF

    def write(self, address, data):
        if address==constants.NR10:
            self.channel1.set_audio_sweep(data)
        elif address == constants.NR11:
            self.channel1.set_audio_length(data)
        elif address == constants.NR12:
            self.channel1.set_audio_envelope(data)
        elif address == constants.NR13:
            self.channel1.set_audio_frequency(data)
        elif address == constants.NR14:
            self.channel1.set_audio_playback(data)
        
        elif address == constants.NR21:
            self.channel2.set_audio_length(data)
        elif address == constants.NR22:
            self.channel2.set_audio_envelope(data)
        elif address == constants.NR23:
            self.channel2.set_audio_frequency(data)
        elif address == constants.NR24:
            self.channel2.set_audio_playback(data)
        
        elif address == constants.NR30:
            self.channel3.set_audio_enable(data)
        elif address == constants.NR31:
            self.channel3.set_audio_length(data)
        elif address == constants.NR32:
            self.channel3.set_audio_level(data)
        elif address == constants.NR33:
            self.channel3.set_audio_frequency(data)
        elif address == constants.NR34:
            self.channel3.set_audio_playback(data)
        
        elif address == constants.NR41:
            self.channel4.set_audio_length(data)
        elif address == constants.NR42:
            self.channel4.set_audio_envelope(data)
        elif address == constants.NR43:
            self.channel4.set_audio_polynomial(data)
        elif address == constants.NR44:
            self.channel4.set_audio_playback(data)
        
        elif address == constants.NR50:
            self.set_output_level(data)
        elif address == constants.NR51:
            self.set_output_terminal(data)
        elif address == constants.NR52:
            self.set_output_enable(data)
        
        elif address >= constants.AUD3WAVERAM and \
             address <= constants.AUD3WAVERAM + 0x3F:
            self.channel3.set_audio_wave_pattern(address, data)

    def update_audio(self):
        if (self.outputEnable & 0x80) == 0:
            return
        if (self.outputEnable & 0x01) != 0:
            self.channel1.update_audio()
        if (self.outputEnable & 0x02) != 0:
            self.channel2.update_audio()
        if (self.outputEnable & 0x04) != 0:
            self.channel3.update_audio()
        if (self.outputEnable & 0x08) != 0:
            self.channel4.update_audio()

    def mix_audio(self, buffer, length):
        if (self.outputEnable & 0x80) == 0:
            return
        if (self.outputEnable & 0x01) != 0:
            self.channel1.mix_audio(buffer, length)
        if (self.outputEnable & 0x02) != 0:
            self.channel2.mix_audio(buffer, length)
        if (self.outputEnable & 0x04) != 0:
            self.channel3.mix_audio(buffer, length)
        if (self.outputEnable & 0x08) != 0:
            self.channel4.mix_audio(buffer, length)

     # Output Control
    def get_output_level(self):
        return self.outputLevel

    def get_output_terminal(self):
        return self.outputTerminal

    def get_output_enable(self):
        return self.outputEnable

    def set_output_level(self, data):
        self.outputLevel = data

    def set_output_terminal(self, data):
        self.outputTerminal = data

    def set_output_enable(self, data):
        self.outputEnable = (self.outputEnable & 0x7F) | (data & 0x80)
        if (self.outputEnable & 0x80) == 0x00:
            self.outputEnable &= 0xF0


# SOUND DRIVER -----------------------------------------------------------------


class SoundDriver(object):
    
    def __init__(self):
        self.enabled = True
        self.sampleRate = 44100
        self.channelCount = 2
        self.bitsPerSample = 8
    
    def is_enabled(self):
        return self.enabled
    
    def get_sample_rate(self):
        return self.sampleRate
    
    def get_channels(self):
        return self.channelCount
    
    def get_bits_per_sample(self):
        return self.bitsPerSample
    
    def start(self):
        pass
        
    def stop(self):
        pass
    
    def write(self, buffer, length):
        pass
