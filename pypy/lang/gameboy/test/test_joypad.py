from pypy.lang.gameboy.joypad import *
from pypy.lang.gameboy.interrupt import *
from pypy.lang.gameboy import constants

BUTTON_CODE = 0x3

def get_joypad():
    return Joypad(get_driver(), Interrupt())

def get_driver():
    return JoypadDriver()

def get_button():
    return Button(BUTTON_CODE)

# TEST BUTTON ------------------------------------------------------------------

def test_ini():
    value = 0xf
    button = Button(value)
    assert button.oppositeButton == None
    assert button.codeValue == value
    assert button.isPressed() == False
    
    button2 = Button(value, button)
    assert button2.oppositeButton == button
    assert button2.codeValue == value
    
def test_getCode():
    button = get_button()
    assert button.getCode() == 0
    button.press()
    assert button.getCode() == button.codeValue
    
def test_press_release():
    button = get_button()
    button2 = get_button()
    button.oppositeButton = button2;
    button2.press()
    assert button2.isPressed() == True
    button.press()
    assert button.isPressed() == True
    assert button2.isPressed() == False
    button.release()
    assert button.isPressed() == False
    assert button2.isPressed() == False

# TEST JOYPAD DRIVER -----------------------------------------------------------

def test_ini():
    driver = get_driver()
    assert driver.raised == False
    assert driver.getButtonCode() == 0
    assert driver.getDirectionCode() == 0
    
def test_isRaised():
    driver = get_driver()
    driver.raised = True
    assert driver.raised == True
    assert driver.isRaised() == True
    assert driver.raised == False
    
def test_button_code_values():
    driver = get_driver()
    assert driver.up.codeValue == constants.BUTTON_UP 
    assert driver.right.codeValue == constants.BUTTON_RIGHT   
    assert driver.down.codeValue == constants.BUTTON_DOWN
    assert driver.left.codeValue == constants.BUTTON_LEFT
    assert driver.select.codeValue == constants.BUTTON_SELECT
    assert driver.start.codeValue == constants.BUTTON_START
    assert driver.a.codeValue == constants.BUTTON_A
    assert driver.b.codeValue == constants.BUTTON_B
    
    
def test_toggle_opposite_directions():
    driver = get_driver()
    directions = [(driver.buttonUp, driver.up, driver.down),
                 (driver.buttonDown, driver.down, driver.up),
                 (driver.buttonLeft, driver.left, driver.right),
                 (driver.buttonRight, driver.right, driver.left)]
    for dir in directions:
        toggleFunction = dir[0]
        button = dir[1]
        oppositeButton = dir[2]
        driver.reset()
        
        oppositeButton.press()
        assert driver.raised == False
        assert button.isPressed() == False
        assert oppositeButton.isPressed() == True
        assert driver.getDirectionCode() == oppositeButton.codeValue
        assert driver.getButtonCode() == 0
        
        toggleFunction()
        assert driver.raised == True
        assert button.isPressed() == True
        assert oppositeButton.isPressed() == False
        assert driver.getDirectionCode() == button.codeValue
        assert driver.getButtonCode() == 0
        
        toggleFunction(False)
        assert button.isPressed() == False
        assert oppositeButton.isPressed() == False
        assert driver.getDirectionCode() == 0
        assert driver.getButtonCode() == 0
    
    
def test_toggle_buttons():
    driver = get_driver()
    buttons = [(driver.buttonSelect, driver.select),
                 (driver.buttonStart, driver.start),
                 (driver.buttonA, driver.a),
                 (driver.buttonB, driver.b)]
    for button in buttons:
        toggleFunction = button[0]
        button = button[1]
        driver.reset()
        
        assert button.isPressed() == False
        assert driver.getButtonCode() == 0
        assert driver.getDirectionCode() == 0
        
        toggleFunction()
        assert driver.raised == True
        assert button.isPressed() == True
        assert driver.getButtonCode() == button.codeValue
        assert driver.getDirectionCode() == 0
        
        toggleFunction(False)
        assert button.isPressed() == False
        assert driver.getButtonCode() == 0
        assert driver.getDirectionCode() == 0

# TEST JOYPAD ------------------------------------------------------------------

def test_reset(joypad=None):
    if joypad == None:
        joypad = get_joypad()
    assert joypad.joyp == 0xF
    assert joypad.cycles == constants.JOYPAD_CLOCK
        
def test_emulate():
    joypad = get_joypad()
    ticks = 2
    cycles = joypad.cycles
    joypad.emulate(ticks)
    assert cycles - joypad.cycles == ticks

def test_emulate_zero_ticks():
    joypad = get_joypad()
    joypad.cycles = 2
    ticks = 2
    joypad.emulate(ticks)
    assert joypad.cycles == constants.JOYPAD_CLOCK
    
def test_emulate_zero_ticks_update():   
    joypad = get_joypad() 
    value = 0x1
    joypad.joyp = value
    joypad.driver.buttonCode = 0x4
    joypad.driver.raised = True
    joypad.cycles = 2
    ticks = 2
    joypad.emulate(ticks)
    assert joypad.cycles == constants.JOYPAD_CLOCK
    assert joypad.joyp == value
    assert joypad.buttonCode == 0
    
def test_read_write():
    joypad = get_joypad()
    value = 0x2
    joypad.write(constants.JOYP, value)
    joyp = 0xC + (value & 0x3)
    assert joypad.joyp == joyp
    joyp = (joyp << 4) + 0xF
    assert joypad.read(constants.JOYP) == joyp
    assert joypad.read(constants.JOYP+1) == 0xFF
    # no change on writing the wrong address
    joypad.write(constants.JOYP+1, value+1)
    assert joypad.read(constants.JOYP) == joyp
    
    
def test_update():
    joypad = get_joypad()
    joypad.driver.buttonSelect()
    assert joypad.driver.getButtonCode() == constants.BUTTON_SELECT
    joypad.driver.buttonUp()
    assert joypad.driver.getDirectionCode() == constants.BUTTON_UP
    assert joypad.buttonCode == 0xF
    joypad.joyp = 0x1
    joypad.update()
    assert joypad.buttonCode == (constants.BUTTON_SELECT | constants.BUTTON_UP)
    
    joypad.joyp = 0x2
    joypad.update()
    assert joypad.buttonCode == (constants.BUTTON_SELECT | constants.BUTTON_UP)
    
    joypad.joyp = 0x3
    joypad.update()
    assert joypad.buttonCode == 0xF
    
    
    