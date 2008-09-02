#!/bin/bash
rm -rf *.txt

romPath=~/Ausbildung/08_UNIBE_FS/bachelor/docs/roms
executable=/pypy-dist/pypy/lang/gameboy/gameboyTest.py

python2.5 $executable $romPath/Megaman.gb         >> logs/megaman.txt 
python2.5 $executable $romPath/KirbysDreamLand.gb >> logs/kirbysDreamland.txt
python2.5 $executable $romPath/SuperMarioLand.gb  >> logs/superMario.txt
python2.5 $executable              			      >> logs/rom9.txt


python parseTests.py