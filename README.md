simms
=====

Creates empty measurement sets using the the CASA simulate tool. 

Requires
-----
[casapy](http://casa.nrao.edu/casa_obtaining.shtml)  
pyrap ( [debian](https://launchpad.net/~ska-sa/+archive/ubuntu/main) or [general build](https://code.google.com/p/pyrap/wiki/BuildInstructions)  )
numpy


Install 
---
```
$ git clone https://github.com/SpheMakh/simms
$ cd simms && sudo python setup.py install 
```

Examples
------
To get farmiliar with options run: `simms --help` ;)

The antenna positions can be specified as a CASA Table or an ASCII file. Bellow is an example of you can an empty MS using both formats:

**NOTE**: Some antenna tables are provided in Simms/observatories. Run the examples below in the `simms` directory or change the paths of the antenna files accordingly in the lines bellow. 

* **CASA Table** `KAT7_ANTENNAS`
```
simms -T kat-7 -t casa -l test_casa -dec -30d0m0s -ra 0h0m0s -st 1 -dt 60 -f0 1.4GHz -nc 4 -df 10MHz Simms/observatories/KAT7_ANTENNAS
```

* **ASCII**   `vlac.enu.itrf`
```
 simms -T vla -t ascii -cs itrf -l test_ascii -dec 30d0m0s -ra 0h0m0s -st 1 -dt 60 -f0 1.4GHz -nc 4 -df 10MHz Simms/observatories/vlac.itrf.txt
```

In both cases, we create an empty MS (VLA-A and KAT-7) at 1400MHz with 4 10MHz channels, the observtion is 1hr and has a 60s integrations time.
