********************************************
K-Series Robot Operating System (KROS): Core
********************************************

**KROS Core** provides the core functionality of a *K-Series Robot Operating
System (KROS)*, a Raspberry Pi based robot written in Python 3, whose prototype
hardware implementations are the **KR01** and **KD01** robots.

.. figure:: https://service.robots.org.nz/wiki/attach/KR01/KR01-0533-1280x584.jpg
   :width: 640px
   :align: center
   :height: 292px
   :alt: The KR01 Robot

   The KR01 Robot prowling the front deck.

The *kros-core* library provides essential support designed as the basis of a
`Behaviour-Based Systems (BBS) <https://en.wikipedia.org/wiki/Behavior-based_robotics>`_.
This library is relatively "low-level" and could be used for any Python 3 based robot.
It will be distributed via `PyPy <https://pypi.org/>`_ so that its components can be
easily installed from the command line.

The basic function is for sensors to act as "Publishers" in a "Publish-Subscribe" model,
firing event-laden messages onto an asynchronous message bus. Subscribers to the bus can
filter which event types they are interested in. The flow of messages are thus filtered
through the Subscribers, who pass on to an Arbitrator messages they have consumed. Once all
Subscribers have acknowledged a message it is passed to a Garbage Collector (a specialised
Subscriber).

Each event type has a fixed priority. The Arbitrator receives this flow of events and
passes along to a Controller the highest priority event for a given clock cycle (typically
50ms/20Hz). The Controller takes the highest priority event and for that clock cycle
initiates any Behaviours registered for that event type.

For example, a Subscriber that filters on bumper events receives a message whose event
type is Event.BUMPER_PORT (the left/port side bumper has been triggered). This Subscriber
passes the Payload of its Message to the Arbitrator. Since a bumper press is a relatively
high priority event it's likely that it will be the highest priority and is therefore
passed on to the Controller.  If an avoidance Behaviour &mdash; let's call it AVOID_PORT
&mdash; has been registered with the Controller, it is called and the robot will begin
whatever the AvoidPort behaviour entails, perhaps stopping, backing up while turning
clockwise, then proceeding forward again on a new trajectory.


Features
********

* message and event handling
* an asynchronous message bus that forms the basis of a `Subsumption Architecture <https://en.wikipedia.org/wiki/Subsumption_architecture>`_ [#f1]_, with an "exactly-once' message delivery guarantee
* YAML-based configuration
* timestamped, multi-level, colorised [#f2]_ logging
* written in Python 3

.. [#f1] Uses finite state machines, an asynchronous message bus, an arbitrator and controller for task prioritisation.
.. [#f2] Colorised console output tested only on Unix/Linux operating systems.


Requirements
************

This library requires Python 3.8.5 or newer. Some portions (modules) of the KROS
code will only run on a Raspberry Pi, though KROS Core should function
independently of the various Pi libraries.

KROS requires installation of a number of dependencies (support libraries),
which should be automatically installed via pip3 when you installed kros-core::


If you install kros-core by cloning the repository, you can install its
dependencies either by running the setup.py script (as described below) or
manually via pip3::

    sudo pip3 install -e .

or directly::

    sudo pip3 install colorama pytest pyyaml psutil

Alternately, use the setup.py script to install dependencies. As this is a work
in progress you may find error messages referring to missing libraries; if so,
you will need to install these manually. 


Installation
************

While this is a work-in-progress the aim is that the pip3 installer will handle
installation of all dependencies, so that you may be able to install via the
command line::

    pip3 install --user kros-core

This ability will be available once kros-core has been published to PyPI.

While numpy can be installed via pip3 we recommend using the available library
directly from the Linux repository::

    sudo apt-get install python3-numpy


Usage
*****

The current functionality is entirely as a robot simulator, i.e., once installed
it's possible to run the a test script without requiring an actual robot. Execute
the script via::

    pub_sub_test.py

to start the message bus event loop. The robot sensors are simulated via key
presses. You can type '?' to see a display mapping which key fires which event
(apologies if your keyboard doesn't match mine). You can type 'i' for system 
information. To quit, type 'q' or Ctrl-C.

For example, you can type 'z' to display the motor status in a loop, then '8' 
for Full Ahead (maximum speed), increase or decrease port and starboard motor
velocity with the four keys ('[', ']', ';', "'") near the Return key, brake 
(slow down gradually) to a stop with '-'. 

Typing 'd' simulates the center infrared sensor being triggered.


Status
******

This project should currently be considered a "**Technology Preview**".

The files in the repository function largely as advertised but the overall state
of KROS is not yet complete — it's still very much a work-in-progress and there
are still some pieces missing that are not quite "ready for prime time."
Demonstrations and included tests (including the pytest suite) either pass
entirely or are close to passing.

The project is being exposed publicly so that those interested can follow its
progress.


Support & Liability
*******************

This project comes with no promise of support or acceptance of liability. Use at
your own risk.


Further Information
*******************

More information can be found on the *New Zealand Personal Robotic Group (NZPRG) Blog* at:

* `The KR01 Robot Project <https://robots.org.nz/2019/12/08/kr01/>`_

and the *NZPRG Wiki* at:

* `KR01 Robot <https://service.robots.org.nz/wiki/Wiki.jsp?page=KR01>`_

Please note that the documentation in the code will likely be more current
than this README file, so please consult it for the "canonical" information.


Execution
*********

To force the Raspberry Pi to prioritise execution of a python script, use
the 'chrt' command, e.g.::

    chrt -f 5 python3 ./my_script.py


Copyright & License
*******************

All contents (including software, documentation and images) Copyright 2020-2021
by Murray Altheim. All rights reserved.

Software and documentation are distributed under the MIT License, see LICENSE
file included with project.

