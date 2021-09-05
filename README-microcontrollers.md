-----------------------------------------
  README - Microcontrollers on the KR01
-----------------------------------------

The KR01 currently hosts two microcontrollers:

  1. an ESP32-based TinyPICO used as an external clock, and,
     mounted at:        /dev/ttyUSB0
     open with:         rshell -p /dev/ttyUSB0
     script installed:  ./main_ext_clock_esp32.py

  2. an Itsy Bitsy RP2040, currently not doing much of anything
     mounted at:        /dev/ttyACM0
     open with:         rshell -p /dev/ttyACM0
     script installed:  ./main_ext_clock_rp2040.py

Note that on your own computer the actual tty used may differ.

To connect to the microcontroller, use rshell with the board's port as an argument.

When in rshell, the executable script can be found at:  /pyboard/main.py

The 'edit' command will by default open vim.

#EOF
