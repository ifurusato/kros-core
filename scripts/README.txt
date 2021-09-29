README: Script Macros

This directory contains scripts that will be loaded by the MacroProcessor (core/macro.py)
stored in the script library, and used as a schedule of statements, each representing an
event and a duration.

All *.py files in this directory will be executed/imported. Use template.py as an example
of how to write a macro script.

Note that even Python files that don't actually create a script macro (e.g., nada.py)
will be imported if they are in this directory, so be careful about side effects.

