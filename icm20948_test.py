#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2010-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-08-03
# modified: 2021-11-15
#
#      X        
#      ^
#  Y < Z    _______________
#           |             |
#           |  ICM 20948  |
#           |             |
#           |_           _|
#             |_I_I_I_I_|
#

import sys, time, traceback, math
from colorama import init, Fore, Style
init(autoreset=True)

try:
    from icm20948 import ICM20948
except ImportError as ie:
    sys.exit("This script requires the icm20948 module.\n"\
           + "Install with: pip3 install --user icm20948")
from rgbmatrix5x5 import RGBMatrix5x5
from colorsys import hsv_to_rgb

from core.logger import Level, Logger
from core.config_loader import ConfigLoader
from core.convert import Convert

#X = 0
#Y = 1
#Z = 2
#AXES = Y, Z

# ..............................................................................
class IMU():
    '''
        An ICM20948-based Inertial Measurement Unit (IMU).
    '''
    def __init__(self, config, level):
        super().__init__()
        self._log = Logger('imu', level)
        if config is None:
            raise ValueError('no configuration provided.')
#       _config = config['kros'].get('imu')
        self._icm20948 = ICM20948(i2c_addr=0x69)
        self._amin = list(self._icm20948.read_magnetometer_data())
        self._amax = list(self._icm20948.read_magnetometer_data())
        self._log.info('amin: {}; amax: {}'.format(type(self._amin), type(self._amax)))
        self._log.info('ready.')

    def read_magnetometer(self):
        return self._icm20948.read_magnetometer_data()

    def read_accelerometer_gyro(self):
        return self._icm20948.read_accelerometer_gyro_data()

#    def heading_from_magnetometer(self, mag):
#        mag = list(mag)
#        for i in range(3):
#            v = mag[i]
#            if v < self._amin[i]:
#                self._amin[i] = v
#            if v > self._amax[i]:
#                self._amax[i] = v
#            mag[i] -= self._amin[i]
#            try:
#                mag[i] /= self._amax[i] - self._amin[i]
#            except ZeroDivisionError:
#                pass
#            mag[i] -= 0.5
#    
#        heading = math.atan2(mag[AXES[0]], mag[AXES[1]])
#        if heading < 0:
#            heading += 2 * math.pi
#        heading = math.degrees(heading)
#        heading = int(round(heading))
#        return heading

def get_accel_color(value):
    if value < -1.0:
        return Fore.RED
    elif value > 1.0:
        return Fore.GREEN
    else:
        return Fore.YELLOW

def get_gyro_color(value):
    if value < -30.0:
        return Fore.RED
    elif value > 30.0:
        return Fore.GREEN
    else:
        return Fore.YELLOW

def get_mag_color(value):
    if value < -30.0:
        return Fore.RED
    elif value > 30.0:
        return Fore.GREEN
    else:
        return Fore.YELLOW

# main .........................................................................
def main(argv):

    _GYRO_ONLY  = False
    _ACCEL_ONLY = False
    _MAG_ONLY   = True

    try:

        # read YAML configuration
        _config = ConfigLoader().configure()

        _rgbmatrix5x5 = RGBMatrix5x5()
        _rgbmatrix5x5.set_clear_on_exit()
        _rgbmatrix5x5.set_brightness(0.8)

        _offset = 135

        _imu = IMU(_config, Level.INFO)

        while True:
#           ax, ay, az, gx, gy, gz = _imu.read_accelerometer_gyro()
            if _GYRO_ONLY:
                acc = _imu.read_accelerometer_gyro()
                _x = acc[3]
                _y = acc[4]
                _z = acc[5]
                print(Fore.CYAN + 'Gyro:\t'
                        + get_gyro_color(_x) + '{:05.2f}\t'.format(_x)
                        + get_gyro_color(_y) + '{:05.2f}\t'.format(_y)
                        + get_gyro_color(_z) + '{:05.2f}\t'.format(_z) )
            elif _ACCEL_ONLY:
                acc = _imu.read_accelerometer_gyro()
                _x = acc[0]
                _y = acc[1]
                _z = acc[2]
                print(Fore.CYAN + 'Accel:\t'
                        + get_accel_color(_x) + '{:05.2f}\t'.format(_x)
                        + get_accel_color(_y) + '{:05.2f}\t'.format(_y)
                        + get_accel_color(_z) + '{:05.2f}\t'.format(_z) )
            elif _MAG_ONLY:
                mag = _imu.read_magnetometer()
                _x = mag[0]
                _y = mag[1]
                _z = mag[2]

                heading = Convert.heading_from_magnetometer(_imu._amin, _imu._amax, mag, _offset)
                r, g, b = [int(c * 255.0) for c in hsv_to_rgb(heading / 360.0, 1.0, 1.0)]
                _rgbmatrix5x5.set_all(r, g, b)
                _rgbmatrix5x5.show()
                print(Fore.CYAN + 'Mag:\t' 
                        + Fore.RED   + '{:05.2f}\t'.format(_x)
                        + Fore.GREEN + '{:05.2f}\t'.format(_y)
                        + Fore.BLUE  + '{:05.2f}\t'.format(_z)
                        + Fore.CYAN  + 'Heading: {:d}°'.format(heading))
            else:
                acc = _imu.read_accelerometer_gyro()
#               x, y, z = _imu.read_magnetometer()
                mag = _imu.read_magnetometer()
                heading = Convert.heading_from_magnetometer(_imu._amin, _imu._amax, mag, _offset)
                print(Fore.CYAN    + 'Accel: {:05.2f} {:05.2f} {:05.2f} '.format(acc[0], acc[1], acc[2]) \
                    + Fore.YELLOW  + '\tGyro: {:05.2f} {:05.2f} {:05.2f} '.format(acc[3], acc[4], acc[5]) \
                    + Fore.MAGENTA + '\tMag: {:05.2f} {:05.2f} {:05.2f}  '.format(mag[0], mag[1], mag[2]) \
                    + Fore.GREEN   + '\tHeading: {:d}°'.format(heading))
            time.sleep(0.25)

    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')

    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting imu: {}'.format(traceback.format_exc()))

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
