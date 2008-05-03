
from pypy.lang.gameboy import constants

class Joypad(object):
    """
    PyBoy GameBoy (TM) Emulator
     
    Joypad Input
    """

    def __init__(self, joypadDriver, interrupt):
        self.driver = joypadDriver
        self.interrupt = interrupt
        self.reset()

    def reset(self):
        self.joyp = 0xF
        self.buttonCode = 0xF
        self.cycles = constants.JOYPAD_CLOCK

    def getCycles(self):
        return self.cycles

    def emulate(self, ticks):
        self.cycles -= ticks
        if (self.cycles <= 0):
            if (self.driver.isRaised()):
                self.update()
            self.cycles = constants.JOYPAD_CLOCK

    def write(self, address, data):
        if (address == constants.JOYP):
            self.joyp = (self.joyp & 0xC) + (data & 0x3)
            self.update()

    def read(self, address):
        if (address == constants.JOYP):
            return (self.joyp << 4) + self.buttonCode
        return 0xFF

    def update(self):
        oldButtons = self.buttonCode
        if self.joyp == 0x1:
            self.buttonCode = self.driver.getButtonCode()
        elif self.joyp == 0x2:
            self.buttonCode = self.driver.getDirectionCode()
        else:
            self.buttonCode  = 0xF

        if oldButtons != self.buttonCode:
            self.interrupt.raiseInterrupt(constants.JOYPAD)


# ------------------------------------------------------------------------------


class JoypadDriver(object):
    """
    Maps the Input to the Button and Direction Codes
    """
    def __init__(self):
        self.raised = False
        self.createButtons()
        self.reset()
        
    def createButtons(self):
        self.up = Button(constants.BUTTON_UP)
        self.right = Button(constants.BUTTON_RIGHT)
        self.down = Button(constants.BUTTON_DOWN)
        self.left = Button(constants.BUTTON_LEFT)
        self.start = Button(constants.BUTTON_START)
        self.select = Button(constants.BUTTON_SELECT)
        self.a = Button(constants.BUTTON_A)
        self.b = Button(constants.BUTTON_B)
        self.addOppositeButtons()
        self.createButtonGroups()
        
    def addOppositeButtons(self):
        self.up.oppositeButton = self.down
        self.down.oppositeButton = self.up
        self.left.oppositeButton = self.right
        self.right.oppositeButton = self.left
        
    def createButtonGroups(self):
        self.directions = [self.up, self.right, self.down, self.left]
        self.buttons = [self.start, self.select, self.a, self.b]
        
    def getButtons(self):
        return self.buttons
    
    def getDirections(self):
        return self.directions
    
    def getButtonCode(self):
        code = 0
        for button in self.buttons:
            code |= button.getCode()
        return code
        
    def getDirectionCode(self):
        code = 0
        for button in self.directions:
            code |= button.getCode()
        return code
    
    def isRaised(self):
        raised = self.raised
        self.raised = False
        return raised
    
    def reset(self):
        self.raised = False
        self.releaseAllButtons()

    def releaseAllButtons(self):
        self.releaseButtons()
        self.releaseDirections()
        
    def releaseButtons(self):
        self.up.release()
        self.right.release()
        self.down.release()
        self.left.release()
        
    def releaseDirections(self):
        self.start.release()
        self.select.release()
        self.a.release()
        self.b.release()
        
    def buttonUp(self, pressed=True):
        self.up.toggleButton(pressed)
        self.raised = True
    
    def buttonRight(self, pressed=True):
        self.right.toggleButton(pressed)
        self.raised = True
    
    def buttonDown(self, pressed=True):
        self.down.toggleButton(pressed)
        self.raised = True
    
    def buttonLeft(self, pressed=True):
        self.left.toggleButton(pressed)
        self.raised = True
    
    def buttonStart(self, pressed=True):
        self.start.toggleButton(pressed)
        self.raised = True
    
    def buttonSelect(self, pressed=True):
        self.select.toggleButton(pressed)
        self.raised = True
    
    def buttonA(self, pressed=True):
        self.a.toggleButton(pressed)
        self.raised = True
    
    def buttonB(self, pressed=True):
        self.b.toggleButton(pressed)
        self.raised = True
    
  
# ------------------------------------------------------------------------------  
    
    
class Button(object):
    
    def __init__(self, codeValue, oppositeButton=None):
        self.codeValue = codeValue
        self.oppositeButton = oppositeButton
        self.pressed = False
        
    def getCode(self):
        if self.pressed:
            return self.codeValue
        else:
            return 0
        
    def toggleButton(self, pressed=True):
        if pressed:
            self.press()
        else:
            self.release()
            
    def release(self):
        self.pressed = False
        
    def press(self):
        if self.oppositeButton is not None:
            self.oppositeButton.release()
        self.pressed = True
        
    def isPressed(self):
        return self.pressed