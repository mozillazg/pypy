"""
Mario GameBoy (TM) Emulator
 
Timer and Divider
"""

class Timer(object):

     # Registers
     #int
    div = 0;
    tima = 0;
    tma = 0;
    tac = 0;

    dividerCycles = 0;
    timerCycles = 0;
    timerClock = 0;


     # Interrupt Controller Interrupt
    interrupt = None;

    def __init__(self, interrupt):
        self.interrupt = interrupt;
        self.reset();


    def reset(self):
        self.div = 0;
        self.dividerCycles = constants.DIV_CLOCK;
        self.tima = self.tma = self.tac = 0x00;
        self.timerCycles = self.timerClock = constants.TIMER_CLOCK[self.tac & 0x03];


    def write(self,  address, data):
        if address==constants.DIV:
            self.setDivider(data);
        elif address==constants.TIMA:
            self.setTimerCounter(data);
        elif address==constants.TMA:
            self.setTimerModulo(data);
        elif address==constants.TAC:
            self.setTimerControl(data);
    


    def read(self,  address):
        if address==constants.DIV:
            return self.getDivider();
        elif address==constants.TIMA:
            return self.getTimerCounter();
        elif address==constants.TMA:
            return self.getTimerModulo();
        elif address==constants.TAC:
            return self.getTimerControl();
        return 0xFF;


    def setDivider(self,  data):
        #DIV register resets on write
        self.div = 0;


    def setTimerCounter(self,  data):
        self.tima = data;


    def setTimerModulo(self,  data):
        self.tma = data;


    def setTimerControl(self,  data):
        if ((self.tac & 0x03) != (data & 0x03)):
            self.timerCycles = self.timerClock = constants.TIMER_CLOCK[data & 0x03];
        self.tac = data;


    def getDivider(self):
        return self.div;


    def getTimerCounter(self):
        return self.tima;


    def getTimerModulo(self):
        return self.tma;


    def getTimerControl(self):
        return 0xF8 | self.tac;


    def cycles(self):
        if ((self.tac & 0x04) != 0 and self.timerCycles < self.dividerCycles):
                return self.timerCycles;
        return self.dividerCycles;


    def emulate(self,  ticks):
        self.emulateDivider(ticks);
        self.emulateTimer(ticks);


    def emulateDivider(self,  ticks):
        self.dividerCycles -= ticks;
        while (self.dividerCycles <= 0):
            self.div = (self.div + 1) & 0xFF;
            self.dividerCycles += constants.DIV_CLOCK;
    


    def emulateTimer(self,  ticks):
        if ((self.tac & 0x04) != 0):
            self.timerCycles -= ticks;

            while (self.timerCycles <= 0):
                self.tima = (self.tima + 1) & 0xFF;
                self.timerCycles += self.timerClock;

                if (self.tima == 0x00):
                    self.tima = self.tma;
                    self.interrupt.raiseInterrupt(constants.TIMER);
    
