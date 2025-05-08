
# KROS Core: Operating System for the K-Series Robots

![The KRZ03 robot](https://service.robots.org.nz/wiki/attach/KRZ03/krz03-deck.jpg)

**KROS Core** provides the core functionality of the K-Series robots, i.e., a Raspberry
Pi-based robot OS written in Python 3. KROS Core is intended as a basis for developing 
a robot that uses at its core an asynchronous publish-subscribe message bus.

This repository represents the stripped-down core of the Python robot OS as has been used
on the KR01, KD01, MR01 and KRZ03 robots. It contains no support for sensors, motor 
controllers, any Subscribers or Publishers tied to hardware. As such, it is a standalone 
application.

If you are looking for support for hardware such as proximity sensors, IMUs, motor 
controllers, there are numerous examples of these classes on the repositories of the 
robots themselves:

* [KROS, the operating system of the KR01 and KD01 robots](https://github.com/ifurusato/kros)
* [MROS, the operating system of the MR01 Mars rover](https://github.com/ifurusato/mros)
* [KRZOS, the operating system of the KRZ03 Mecanum robot](https://github.com/ifurusato/krzos)

See also:

* [Behaviour-based Robotics, its scope and its prospects](http://www.sci.brooklyn.cuny.edu/~sklar/teaching/boston-college/s01/mc375/iecon98.pdf), Andreas Birk, Vrije Universiteit Brussel, Artificial Intelligene Laboratory, 1988
* [Intelligence without representation](https://people.csail.mit.edu/brooks/papers/representation.pdf), Rodney A Brooks, MIT Artificial Intelligence Laboratory, 1987
* [Autonomous Agents](https://www.am.chalmers.se/~wolff/AA/AutonomousAgents.html), Krister Wolff, Chalmers University of Technology, Göteborg, Sweden, and particularly chapter 3, _[Behaviour-based robotics](https://www.am.chalmers.se/~wolff/AA/Chapter3.pdf)_, 2008


## Background

The *KROS* library provides essential support designed as the basis of a
[Behaviour-Based Robotic (BBR)](https://en.wikipedia.org/wiki/Behavior-based_robotics)
(AKA Behaviour-Based Systems or BBS). This library is relatively "low-level" and, in 
theory, could be used for any Python 3 based robot.

The basic function is for sensors to act as "Publishers" in a "Publish-Subscribe" model,
firing event-laden messages onto an asynchronous message bus. Subscribers to the bus can
filter which event types they are interested in. The flow of messages are thus filtered
through the Subscribers, who pass on to an Arbitrator messages they have consumed. Once all
Subscribers have acknowledged a message it is passed to a Garbage Collector (a specialised
Subscriber).

Each event type has a fixed priority. The Arbitrator receives this flow of events and
passes along to a Controller the highest priority event. The Controller takes the highest 
priority event and initiates any Behaviours registered for that event type.

There is no inherent system clock as the message bus operates asynchronously, but on 
previous implementations a system clock (typically 50ms/20Hz) optionally regulates how 
often hardware like a motor controller receives updates. 

For example, a BumperSubscriber that filters on bumper events receives a message whose 
event type is `Event.BUMPER_PORT` (the left/port side bumper has been triggered). This 
Subscriber passes the Payload of its Message to the Arbitrator. Since a bumper press is 
a relatively high priority event it's likely that it will be the highest priority and is 
therefore passed on to the Controller. If there has been implemented an AvoidanceBehaviour
registered with the Controller, it is called and the robot will begin whatever the 
Behaviour entails, perhaps stopping, backing up while turning clockwise, then proceeding 
forward again on a new trajectory.


## Software Features

* message and event handling
* an asynchronous message bus that forms the basis of a `[Subsumption Architecture](https://en.wikipedia.org/wiki/Subsumption_architecture) [^1], with an 'exactly-once' message delivery guarantee
* YAML-based configuration
* timestamped, multi-level, colorised [^2] logging
* written in Python 3 (currently 3.11.2)

[^1]: Uses finite state machines, an asynchronous message bus, an arbitrator and controller for task prioritisation.
[^2]: Colorised ANSI console output tested only on Unix/Linux operating systems.


## Requirements

This library requires Python 3.8.5 or newer. It's currently being written using 
Python 3.11.2. KROS Core should function independently of the various Pi libraries.

KROS requires installation of a small number of dependencies (support libraries). 
There is currently no dependency management set up for this project.

First:
```
  sudo apt install python3-pip
```

then:

* [pyyaml](https://pypi.org/project/PyYAML/) with:      `sudo apt install python3-yaml`
* [colorama](https://pypi.org/project/colorama/) with:  `sudo apt install python3-colorama`
* [smbus2](https://pypi.org/project/smbus2/) with:      `sudo apt install python3-smbus2`

To improve performance, if you don't need the avahi-daemon, disable it:
```
   sudo systemctl disable avahi-daemon
```


## Status

This repository is relatively stable, as its classes have been successfully used on
multiple robots.


## Support & Liability

This project comes with no promise of support or acceptance of liability. Use at
your own risk.


## Copyright & License

All contents (including software, documentation and images) Copyright 2020-2025
by Murray Altheim. All rights reserved.

Software and documentation are distributed under the MIT License, see LICENSE
file included with project.

