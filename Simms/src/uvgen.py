#!/usr/bin/env python
## Makes uv-coverage given a list of antenna positions. 
## The antenna positions may be given in either ENU or ITRF coordinates.
## This code is Based on: 
## Synthesis Imaging in Radio Astronomy II, ASP conference series, Vol. 180, 1999, Ch. 2
## Sphesihle Makhathini sphemakh@gmail.com

## Requires 
# numpy
# pylab (matplotlib)
# pyrap
# python-pyephem

import sys
import os
import time
import numpy 
import pylab
import math
import pyrap.measures
import pyrap.quanta as dq
import ephem 
import argparse

PI = math.pi
FWHM = math.sqrt( math.log(256) )

OBSDATA = "uvw points generated using uvgen.py \n"

# Communication functions
def info(string):
    t = "%d/%d/%d %d:%d:%d"%(time.localtime()[:6])
    print "%s ##INFO: %s"%(t, string)

def warn(string):
    t = "%d/%d/%d %d:%d:%d"%(time.localtime()[:6])
    print "%s ##WARNING: %s"%(t, string)

def abort(string,exception=None):
    t = "%d/%d/%d %d:%d:%d"%(time.localtime()[:6])
    exception = exception or SystemExit 
    raise exception("%s ##ABORTING: %s"%(t, string))


class UVCreate(object):

    def __init__(self, antennas, direction, lon=None, lat=None, tel=None, coord_sys='enu'):
        """
            ** Units must be assumed SI, unless stated otherwise. **

            antennas: ASCII file containing (X,Y,Z) or (E,N,U) positions.

            Can also be a list of positions. 

            lat: Lattitude of array

            lon: Longitude of array

            direction: Pointing direction ( specify as "epoch,RA,DEC", e.g 
            direction="J2000,0deg,-30deg)

            coord_sys: Coordinate system of 'antennas'.
            Choices are [itrf,enu], default is itrf.
            
        """

        dm  = pyrap.measures.measures()
        
        self.antennas = antennas
        self.coord_sys = coord_sys 

        if isinstance(direction,str):
            direction = direction.split(',')
        self.direction = direction 

        if tel:
            lon, lat = [ dm.observatory(tel)[x]['value'] for x in 'm0','m1' ]

        if None in [lon,lat]:
            abort('"lon" and "lat" or "tel" have to specified')

        self.lat = lat 
        self.lon = lon 

    
    def enu2itrf(self, antennas=None, lon=None, lat=None):
        """ Converts a list of ENU positions to ITRF positions. 
            Requires a reference positions (lon,lat) in radians. 
           
            Returns the ITRF reference position and the ITRF list of positions.
        """
        
        dm  = pyrap.measures.measures()
        
        antennas = self.antennas if antennas is None else antennas
        lon = lon or self.lon
        lat = lat or self.lat
        
        # convtert reference position to itrf system
        refpos_wgs84 = dm.position('wgs84', dq.quantity(lon, 'rad'),
                       dq.quantity(lat, 'rad'))
        refpos = dm.measure(refpos_wgs84, 'itrf')

        lon,lat,rad = [ refpos[x]['value'] for x in 'm0 m1 m2'.split() ]

        xyz0 = rad*numpy.array( [math.cos(lat)*math.cos(lon),
                        math.cos(lat)*math.sin(lon), math.sin(lat)])
        
        # 3x3 transformation matrix. Each row is a normal vector, i.e the rows are (dE,dN,dU)
        xform = numpy.array([
            [-math.sin(lon), math.cos(lon), 0],
            [-math.cos(lon)*math.sin(lat), -math.sin(lon)*math.sin(lat), math.cos(lat)],
            [math.cos(lat)*math.cos(lon), math.cos(lat)*math.sin(lon), math.sin(lat)]
])
        antennas = numpy.array(antennas)
        xyz = xyz0[numpy.newaxis,:] + antennas.dot(xform)

        return xyz0,xyz


    def source_info(self,tot,lon=None,lat=None,direction=None,date=None):
        
        dm  = pyrap.measures.measures()

        lon = lon or self.lon
        lat = lat or self.lat
        
        # Set up observer        
        obs = ephem.Observer()
        obs.lon, obs.lat = lon,lat
        direction = direction if direction is not None else self.direction

        if isinstance(direction,str):
            direction = direction.split(',')
        ra, dec = [ dm.direction(*direction)[x]['value'] for x in 'm0','m1' ]
        
        def sunrise_equation(lat,dec):
            arg = -math.tan(lat) * math.tan(dec)
            if arg > 1 or arg< -1:
                if lat*dec < 0:
                    warn("Pointing center is always below the horizon!")
                    return 0
                else:
                    info("Pointing center is always above horizon")
                    return 0
            th_ha = math.acos( arg )
            return th_ha
        

        obs.date = date or "%d/%d/%d 0:0:0"%(time.localtime()[:3])
        lst = obs.sidereal_time() 

        def change (angle):
            if angle > 2*PI:
                angle -= 2*PI
            elif angle < 0:
                angle += 2*PI
            return angle
 
        altitude_transit = lambda lat, dec: numpy.sign(lat)*(math.cos(lat)*math.sin(dec) + math.sin(lat)*math.cos(dec) )
                
        # First lets find the altitude at transit (hour angle = 0 or LST=RA)
        # If this is negative, then the pointing direction is below the horizon at its peak.
        #alt_trans = altitude_transit(lat,dec)
        #if alt_trans < 0 :
        #    warn(" Altitude at transit is %f deg, i.e."
        #         " pointing center is always below the horizon!"%(numpy.rad2deg(alt_trans)))
        #    return 0

        altitude = altitude_transit(lat,dec)
        H0 = sunrise_equation(lat,dec)

        # Lets find transit (hour angle = 0, or LST=RA)
        lst,ra = map(change,(lst,ra))
        diff =  (lst - ra )/(2*PI)

        date = obs.date
        obs.date = date - diff
        # LST should now be transit
        transit = change(obs.sidereal_time())
        if ra==0:
            obs.date = date - lst/(2*PI)
        elif abs((transit-ra)/ra) > .05:
            obs.date = date + diff

        # This is the time at transit
        warn(transit*1)
        ih0 = change((obs.date)/(2*PI)%(2*PI))
        # Account for the lower hemisphere
        if lat<0:
            ih0 -= PI
            obs.date -= 0.5
        
        date = obs.date.datetime().ctime()
        return ih0, date, H0, altitude
        
    
    def itrf2uvw(self,h0, antennas=None, dtime=0, direction=None, 
                 lon=None, lat=None, tel=None, coord_sys=None, date=None,
                  save=None, show=False):
        """
            antennas : ITRF antenna positions (3xN)

            direction: Pointing direction ( specify as "epoch,RA,DEC", e.g 
               direction="J2000,0deg,-30deg)

            h0 : Hour angle range [start,end] 

            tel : Get telescope lon,lat from CASA database
        """

        dm  = pyrap.measures.measures()

        if tel:
            lon, lat = [ dm.observatory(tel)[x]['value'] for x in 'm0','m1' ]

        antennas = self.antennas if antennas is None else antennas
        lat = lat or self.lat
        lon = lon or self.lon
        direction = direction or self.direction
        coord_sys = coord_sys or self.coord_sys

        if isinstance(antennas,str):
            antennas = numpy.genfromtxt(antennas)[:,:3]

        if coord_sys == 'enu':
            antennas = self.enu2itrf(antennas, lon, lat)[1]

        dtime = dtime or 10/3600.
        
        if None in [lon,lat]:
            abort('"lon" and "lat" have to specified')
        
        if isinstance(direction,str):
            direction = direction.split(',')

        ra,dec = [ dm.direction(*direction)[x]['value'] for x in 'm0','m1' ]

        
        ntimes = (h0[1]-h0[0])/dtime
        ih0, date, H0, altitude = self.source_info(ntimes*dtime, lon, lat, direction,date=date)
        h0 = ih0 + numpy.linspace(h0[0], h0[1], ntimes)*PI/12. # convert to radians 

        # define matrix that transforms from ITRF (X,Y,Z) to uvw 
        mm = numpy.array([
                [numpy.sin(h0), numpy.cos(h0), 0],
                [-math.sin(dec)*numpy.cos(h0), math.sin(dec)*numpy.sin(h0), math.cos(dec)],
                [math.cos(dec)*numpy.cos(h0), -math.cos(dec)*numpy.sin(h0), math.sin(dec)]
])


        # Get baselines 
        nant = len(antennas)
        bl = []
        for i in range(nant):
            for j in range(i+1,nant):
                bl.append(antennas[i] - antennas[j])

        # Need some numpy array functionality
        bl = numpy.array(bl)

        # Finaly, the u,v,w coordinates!
        u = numpy.outer(mm[0,0],bl[:,0]) + numpy.outer(mm[0,1],bl[:,1]) + numpy.outer(mm[0,2],bl[:,2])
        v = numpy.outer(mm[1,0],bl[:,0]) + numpy.outer(mm[1,1],bl[:,1]) + numpy.outer(mm[1,2],bl[:,2])
        w = numpy.outer(mm[2,0],bl[:,0]) + numpy.outer(mm[2,1],bl[:,1]) + numpy.outer(mm[2,2],bl[:,2])
        
        u, v, w = [ x.flatten() for x in (u, v, w) ]
        pylab.plot(u/1e3, v/1e3, 'b.', ms=1)
        pylab.plot(-u/1e3, -v/1e3, 'r.', ms=1)
        pylab.xlabel(' |uv| [km]')
        pylab.ylabel(' |uv| [km]')

        if save:
            if not isinstance(save, str):
                save = 'uvgen-qazwsx.png'
            pylab.savefig(save)

        if show:
            pylab.show()
        pylab.clf()

        global OBSDATA
        uvmax = max( (u**2 + v**2)**0.5)

        OBSDATA += """
The pointing center is at transit at %s, at which point its altitude is %.3f degress. 
It will be above the horizon for %.3f hours.
The maximum baseline for this array is %.3f. km. The u,v,w points are in meters.
"""%(date,numpy.rad2deg(altitude),2*numpy.rad2deg(H0)/15,uvmax/1e3)
        info(OBSDATA)        
        return numpy.array((u, v, w)).T

if __name__ == '__main__':

    for i, arg in enumerate(sys.argv):
        if (arg[0] == '-') and arg[1].isdigit(): sys.argv[i] = ' ' + arg

    parser = argparse.ArgumentParser(description="Generates the uv-coverage given a list of antenna positions "
                                     "Sphesihle Makhathini sphemakh@gmail.com")
    add = parser.add_argument

    add('antennas', 
        help='File containing antenna positions')
    add('-cs', '--coord-sys', choices=['enu','itrf'], default='enu',
        help='Antenna position coordinate system. Default is "enu" ')
    add('-lon', '--lon', type=float,
        help='Longitude of array in degrees. No default, '
             'this is required if --tel is not specified')
    add('-lat', '--lat', type=float,
        help='Position of array in degrees. No default, '
             'this is required if --tel is not specified')
    add('-T', '--tel', 
        help='Telescope name. Specify this if your telescope is the CASA database.')
    add('-dir', '--direction', 
        help='Pointing direction in the form "reference,ra,dec", e.g "J2000,0deg,-30deg"'
             'No default. This is required')
    add('-st', '--synthesis', type=float,
        help='Synthesis time in hours'
             'No default. This is required')
    add('-dt', '--dtime', type=float,
        help='Integration time in seconds. Default is 10')
    add('-ST', '--start_time', 
        help='Synthesis start time in the form "yyyy/mm/dd hh:mm:ss". '
             'Advanced option: Leave it unspecified if you are not sure its for.')
    add('-o', '--outfile', default='uvgen-qazwsx.txt',
        help='Save uv-points here. Default is uvgen-qazwsx.txt')
    add('-sf', '--savefig',
        help='Save uv-coverage plot here')
    add('-S', '--showfig', action='store_true',
        help='Show uv-coverage plot')
 
    opts = parser.parse_args()
    uv = UVCreate(antennas=opts.antennas, lon=opts.lon, lat=opts.lat, 
                  direction=opts.direction, tel=opts.tel, coord_sys=opts.coord_sys)

    ha = -opts.synthesis/2,opts.synthesis/2
    uvw = uv.itrf2uvw(h0=ha, dtime=opts.dtime/3600.,
            date=opts.start_time, save=opts.savefig, show=opts.showfig)
    numpy.savetxt(opts.outfile,uvw,header=OBSDATA)
    info('FIN!')
