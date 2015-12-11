=====
simms
=====

Creates empty measurement sets using the the CASA simulate tool. 


Requires
========

 * `NRAO CASA <http://casa.nrao.edu/casa_obtaining.shtml>`_
 * `python-casacore <https://github.com/casacore/python-casacore>`_
 * numpy


Install 
=======

Github
------

::

    $ git clone https://github.com/radio-astro/simms
    $ cd simms
    $ python setup.py install


Pip
---

::

    pip install simms



Examples
========

On the command line
-------------------


To get farmiliar with options run: `simms --help` ;)

The antenna positions can be specified as a CASA Table or an ASCII file. Bellow is an example of you can an empty MS
using both formats:

**NOTE**: Some antenna tables are provided in Simms/observatories. Run the examples below in the `simms` directory or
change the paths of the antenna files accordingly in the lines bellow.

CASA Table `KAT7_ANTENNAS`
~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    simms -T kat-7 -t casa -l test_casa -dec -30d0m0s -ra 0h0m0s -st 1 -dt 60 -f0 1.4GHz -nc 4 -df 10MHz Simms/observatories/KAT7_ANTENNAS


ASCII `vlac.enu.itrf`
~~~~~~~~~~~~~~~~~~~~~

::

    simms -T vla -t ascii -cs itrf -l test_ascii -dec 30d0m0s -ra 0h0m0s -st 1 -dt 60 -f0 1.4GHz -nc 4 -df 10MHz Simms/observatories/vlac.itrf.txt


In both cases, we create an empty MS (VLA-A and KAT-7) at 1400MHz with 4 10MHz channels, the observtion is 1hr and has a
60s integrations time.


In Python
---------

::

    from simms import simms

    simms.create_empty_ms(msname="Name_of_ms.MS", tel="kat-7", synthesis=1, pos_type='casa', pos="kat-7_antenna_table")

