from pypy.translator.flex.modules.flex import *


def flash_main(a=1):
	#abutton = Button()
        #abutton.label = "I'm a button!"
        #addChild(abutton)

        for x in range(20):
            abutton = Button()
            abutton.label = "I'm button :" + str(x)
            addChild(abutton)
            
	return a+1



