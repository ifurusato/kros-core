# MicroPython external clock script
from machine import Pin, Timer
gpio6 = Pin(7, Pin.OUT)
tim = Timer()
def tick(timer):
    global gpio6
    gpio6.toggle()
# 50ms = 20Hz, 5ms = 200Hz
tim.init(period=5, mode=Timer.PERIODIC, callback=tick)
