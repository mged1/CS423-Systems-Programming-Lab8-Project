# CS423 Systems Programming Final Project

This project is an integrated SIC/XE assembler and absolute loader simulation.

## Features
- Pass 1 address calculation and symbol table generation
- Pass 2 object code generation
- Immediate, indirect, indexed, PC-relative, and format 4 addressing support
- H, T, and E object-program record generation
- Absolute loader simulation
- 16-byte aligned memory dump

The program generates 'program.obj', loads the object code into virtual memory,
and prints the symbol table, assembly listing, object records, and memory dump.
