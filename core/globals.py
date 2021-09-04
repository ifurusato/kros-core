#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-09-03
# modified: 2021-09-03
#
# global variables shared across all modules

from colorama import init, Fore, Style
init(autoreset=True)

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def init():
    '''
    Creates an application-global dictionary as a way to share objects across
    all modules. Typical usage:

        import core.globalz as globalz
        globalz.init()

        globalz.put('variable_name', _value)
        _value = globalz.get('variable_name')

    You should only need to call 'globalz.init()' on your first module access
    or your main() method.
    '''
    global gvars
    try:
        print(Fore.YELLOW + '📀 globalz.init()')
        if gvars:
            pass
    except Exception as e:
        gvars = {}
        print(Fore.YELLOW + '📀 globalz.init() ' + Style.BRIGHT + 'DEFINE' + Style.NORMAL + ' gvars; error: {}'.format(e))

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def has(key):
    global gvars
    if gvars:
        return gvars.get(key) != None
    else:
        return False

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def put(key, value):
    global gvars
    if not gvars:
        init()
    gvars[key] = value

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
def get(key):
    global gvars
    if not gvars:
        return None
    return gvars.get(key)

#EOF
