-----------------------------------------
  README - Microcontrollers on the KR01
-----------------------------------------

The KR01 currently hosts two microcontrollers:

  1. an ESP32-based TinyPICO used as an external clock, and,

     mounted at:        /dev/ttyUSB0
     open with:         rshell -p /dev/ttyUSB0
     script installed:  ./main_ext_clock_esp32.py

  2. an Itsy Bitsy RP2040, handling the three front bumpers, the mast, 
     back port and starboard digital infrared sensors. This communicates
     over UART to Tx/Rx on the Pi.

     mounted at:        /dev/ttyACM0
     open with:         rshell -p /dev/ttyACM0
     script installed:  ./main_hihp_rp2040.py
     libraries at:      ./upy/

Note that on your own computer the actual tty used may differ.

To connect to the microcontroller, use rshell with the board's port as an argument.

When in rshell, the executable script can be found at:  /pyboard/main.py

The 'edit' command will by default open vim.

NeoPixel Support 
----------------

A NeoPixel support library in MicroPython on the RP2040 may be found at:

    https://github.com/blaz-r/pi_pico_neopixel

The neopixel.py file should be copied to /pyboard/ on the microcontroller.

#EOF
