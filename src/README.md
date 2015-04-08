## uvgen.py
Makes uv-coverage given a list of antenna positions. 
The antenna positions may be given in either ENU or ITRF coordinates.
This code is Based on: 
Synthesis Imaging in Radio Astronomy II, ASP conference series, Vol. 180, 1999, Ch. 2

Requires
----
* numpy  
* pylab (matplotlib)  
* pyrap  
* python-pyephem 


On the command line
-----
First run `./uvgen.py --help` for help  

To test run:
```
./uvgen.py -T meerkat -cs enu -dir J2000,56deg,-30deg -st 4 -dt 120 -o uvgen-test.txt -sf uvcov-test.png -S MeerKAT.enu.txt
``` 


In Python
----
```
import uvgen

# initialise UVCreate instance
uv = UVCreate(antennas=opts.antennas, direction="J2000,0,-30", tel="meerkat", coord_sys="enu")
# Then to generate the uv-coverage for an 8hr synthesis with a 60s integration time run. 
# The ENU to ITRF conversion is done if coord_sys='enu'. 
uvw = uv.itrf2uvw(h0=[-4,4], dtime=60/3600., save='uvcov-test.png', show=True)
```

