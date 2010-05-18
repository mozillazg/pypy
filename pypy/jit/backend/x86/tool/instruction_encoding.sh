#!/bin/bash

# Tool to quickly see how the GNU assembler encodes an instruction
# (AT&T syntax only for now)

while :; do
    echo -n '? '
    read instruction
    echo "$instruction" | as
    objdump --disassemble ./a.out | tail -n +8
    rm -f ./a.out
done
