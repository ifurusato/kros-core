*******************************************
A Python-based Robot Operating System (ROS)
*******************************************

KROS Core provides the core functionality of a *K-Series Robot Operating System* 
(KROS), a Raspberry Pi based robot written in Python 3, whose prototype hardware
implementations are the **KR01** and **KD01** robots.

.. image:: https://service.robots.org.nz/wiki/attach/KR01/KR01-0533-1280x584.jpg
   :width: 1280px
   :align: center
   :height: 584px
   :alt: The KR01 Robot

The kros-core module provides essential support for YAML-based configuration, 
logging, messages and event handling, and the asynchronous message bus that forms 
the basis of a *Subsumption Architecture*.

This module is relatively low-level and could be used for any Python 3 based robot.

More information can be found on the New Zealand Personal Robotic Group (NZPRG) Blog at:

* `The KR01 Robot Project <https://robots.org.nz/2019/12/08/kr01/>`

and the NZPRG wiki at:

* `KR01 Robot <https://service.robots.org.nz/wiki/Wiki.jsp?page=KR01>`

This module will be distributed via PyPy so that its components can be easily 
installed from the command line. 


Features
********

* `Behaviour-Based System (BBS) <https://en.wikipedia.org/wiki/Behavior-based_robotics>`
* `Subsumption Architecture <https://en.wikipedia.org/wiki/Subsumption_architecture>` [#f1]_
* Configuration via YAML file
* written in Python 3

.. [#f1] Uses finite state machines, an asynchronous message queue, an arbitrator and controller for task prioritisation.


Status
******

This project should currently be considered a "**Technology Preview**".

The files in the repository function largely as advertised but the overall state
of the ROS is not yet complete — it's still very much a work-in-progress and
there are still some pieces missing that are not quite "ready for prime time."
Demonstrations and included tests (including the pytest suite) either pass
entirely or are close to passing.

The project is being exposed publicly so that those interested can follow its
progress. 


Installation
************

The ROS requires installation of a number of support libraries. In order to
begin you'll need Python3 (at least 3.8) and pip3, as well as the pigpio library.

While this is a work-in-progress the aim is that the pip3 installer will handle
installation of all dependencies, so that you may be able to install via the 
command line:

    % pip3 install --user kros-core


Support & Liability
*******************

This project comes with no promise of support or liability. Use at your own risk.


Further Information
*******************

For more information check out the `NZPRG Blog <https://robots.org.nz/>` and
`NZPRG Wiki <https://service.robots.org.nz/wiki/>`.

Please note that the documentation in the code will likely be more current
than this README file, so please consult it for the "canonical" information.


Execution
*********

To force the Raspberry Pi to prioritise execution of the python operating
system, use the 'chrt' command, e.g.::

    % chrt -f 5 python3 ./fusion_test.py



Copyright & License
*******************

All contents (including software, documentation and images) Copyright 2020-2021
by Murray Altheim. All rights reserved.

Software and documentation are distributed under the MIT License, see LICENSE
file included with project.

