#!/bin/python

def add_rank(file):
	lines = open(file).readlines()
	lastRank = -1;
	for line in lines[4:]:
		pos = line.find(":")
		try:
			lastRank = int(line[:pos])
			add_rank_opcodes(lastRank, line[pos+2:])
		except :
			add_rank_fetch_opcodes(lastRank, line[pos+2:])
		
			
	
def add_rank_opcodes(rank, opcodes):
	opcodes = opcodes.strip().split(" ")
	for opcode in opcodes:
		op_codes[int(opcode, 16)] += rank
	
def add_rank_fetch_opcodes(rank, opcodes):
	opcodes = opcodes.strip().split(" ")
	for opcode in opcodes:
		fetch_op_codes[int(opcode, 16)] += rank


def print_sorted(table):
	dict = {}
	for i in range(0xFF):
		dict[table[i]] = i 
	keys = dict.keys()
	keys.sort()
	for key in keys:
		if key != 0:
			print "0x%2x: %5i" % (dict[key], key)
	
# --------------------------------------
files = ["superMario.txt", "rom9.txt", "megaman.txt", "kirbysDreamland.txt"]

op_codes = [0] * 0xFF
fetch_op_codes = [0] * 0xFF

for file in files:
	add_rank(file)
	
print_sorted(op_codes)
	