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


Features
********

* YAML-based configuration
* an asynchronous message bus that forms the basis of a `Subsumption Architecture <https://en.wikipedia.org/wiki/Subsumption_architecture>`_ [#f1]_
* message and event handling
* timestamped, multi-level, colorised [#f2]_ logging 
* written in Python 3

.. [#f1] Uses finite state machines, an asynchronous message queue, an arbitrator and controller for task prioritisation.
.. [#f2] Colorised console output tested only on Unix/Linux operating systems.


Requirements
************

This library requires Python 3.8.5 or newer. Some portions (modules) of the KROS
code will only run on a Raspberry Pi, though KROS Core should function independently
of the various Pi libraries.

KROS requires installation of a number of support libraries. In order to begin
you'll need to install pip3 and pytest.


Installation
************

While this is a work-in-progress the aim is that the pip3 installer will handle
installation of all dependencies, so that you may be able to install via the
command line::

    % pip3 install --user kros-core

This ability will be available once kros-core has been published to PyPI.


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

This project comes with no promise of support or liability. Use at your own risk.


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

    % chrt -f 5 python3 ./my_script.py


Copyright & License
*******************

All contents (including software, documentation and images) Copyright 2020-2021
by Murray Altheim. All rights reserved.

Software and documentation are distributed under the MIT License, see LICENSE
file included with project.

