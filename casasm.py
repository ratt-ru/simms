# create a sumulated measurement from given a list of itrf antenna position or an antenna table (Casa table)
import os
import sys
import numpy as np
import math


DEG = 180/math.pi

def get_int_data(tab):
    """ Get inteferometer information from antenna table """

    x,y,z = tab.getcol('POSITION')
    dish_diam = tab.getcol('DISH_DIAMETER')
    station = tab.getcol('STATION')
    mount = tab.getcol('MOUNT')
    return  (x,y,z),dish_diam,station,mount

def enu2xyz (refpos_wgs84,enu):
    """ converts xyz0 + ENU (Nx3 array) into xyz """
    refpos = me.measure(refpos_wgs84,'itrf')
    lon,lat,rad = [ refpos[x]['value'] for x in 'm0','m1','m2' ]
    xyz0 = rad*np.array([math.cos(lat)*math.cos(lon),math.cos(lat)*math.sin(lon),math.sin(lat)])
    # 3x3 transform matrix. Each row is a normal vector, i.e. the rows are (dE,dN,dU)
    xform = np.array([
        [-math.sin(lon),math.cos(lon),0],
        [-math.cos(lon)*math.sin(lat),-math.sin(lon)*math.sin(lat),math.cos(lat)],
        [math.cos(lat)*math.cos(lon),math.cos(lat)*math.sin(lon),math.sin(lat)]
    ])
  
    xyz = xyz0[np.newaxis,:] + enu.dot(xform);
    # return positions
    return xyz


def makems(msname=None,label=None,tel='MeerKAT',pos=None,pos_type='CASA',
           ra='0h0m0s',dec='-30d0m0s',
           synthesis=4,
           scan_length=4,dtime=10,
           freq0=700e6,dfreq=50e6,nchan=1,
           start_time=None,
           stokes='LL LR RL RR',
           noise=0,
           setlimits=False,
           elevation_limit=None,
           shadow_limit=None,
           mspath='.',
           coords='itrf',           
           lon_lat=None,
           noup=False):
    """ Creates an empty measurement set using CASA simulate (sm) tool. """

    # sanity check/correction
    if scan_length > synthesis:
        print 'SIMMS ## WARN: Scan length > synthesis time, setiing scan_length=syntheis'
        scan_length = synthesis
    start_time = start_time or -scan_length/2
 
    if not isinstance(dtime,str):
        dtime = '%ds'%dtime

    if not isinstance(freq0,str):
        freq0 = '%dMHz'%(freq0*1e-6)
    if not isinstance(dfreq,str):
        dfreq = '%dMHz'%(dfreq*1e-6)
    
    stokes = 'LL LR RL RR'
    if msname is None:
        dd = int(qa.unit(dec)['value'])
        dec_sign = '%s%d'%('m' if dd<0 else 'p',abs(dd))
        msname = '%s/%s_%s_%dh%s_%s%s_%dch.MS'%(mspath,label or tel,dec_sign,synthesis,dtime,freq0,dfreq,nchan)

    obs_pos = None
    lon,lat = None,None
    if lon_lat:
        if isinstance(lon_lat,str):
            tmp = lon_lat.split(',')
            lon,lat = ['%sdeg'%i for i in tmp[:2]]
            if len(tmp)>2:
                el = tmp[3]+'m'
            else:
                el = '0m'
            obs_pos = me.position('wgs84',lon,lat,el)
    obs_pos = obs_pos or me.observatory(tel)

    if pos_type.lower() == 'casa':
        tb.open(pos)
        (xx,yy,zz),dish_diam,station,mount = get_int_data(tb)
        tb.close()
    
    elif pos_type.lower() == 'ascii':
        if noup: 
            names = ['x','y','dd','station','mount']
            ncols = 5
        else:
            names = ['x','y','z','dd','station','mount']
            ncols = 6
        dtype = ['float']*ncols
        dtype[-2:] = ['|S20']*2
        pos = np.genfromtxt(pos,names=names,dtype=dtype,usecols=range(ncols))
        
        if coords is 'enu':
            if noup:
                xyz = np.array([pos['x'],pos['y']]).T
            else:
                xyz = np.array([pos['x'],pos['y'],pos['z']]).T
            xyz = enu2xyz(obs_pos,xyz)
            xx,yy,zz = xyz[:,0], xyz[:,1],xyz[:,2]
        else:
            xx,yy,zz = pos['x'],pos['y'],pos['z']

        dish_diam,station,mount = pos['dd'],pos['station'],pos['mount']
        
    sm.open(msname)
    ref_time = me.epoch('IAT','2012/01/01')
    direction = sourcedirection = me.direction('J2000',ra,dec )
   
    sm.setspwindow(spwname = tel,
                   freq = freq0,
                   deltafreq = dfreq,
                   freqresolution = dfreq,
                   nchannels = nchan,
                   stokes= stokes)

    sm.setconfig(telescopename = tel,
                 x = xx,
                 y = yy,
                 z = zz,
                 dishdiameter = dish_diam,
                 mount = mount[0],
                 coordsystem = 'global',
                 referencelocation = obs_pos)

    sm.setfeed(mode='perfect X Y')
    sm.setfield(sourcename='0',sourcedirection=direction)
    sm.settimes(integrationtime = dtime,
                usehourangle = True,
                referencetime = ref_time)

    if setlimits:
        sm.setlimits(shadowlimit=shadow_limit,elevationlimit=elevation_limit)
    sm.setauto(autocorrwt=0.0)
    scan = 0
    end_time = start_time + synthesis

    while (start_time < end_time):
        duration = (scan_length + start_time)*3600
        sm.observe('0',tel,
                   starttime='%ds'%(start_time*3600),
                   stoptime='%ds'%(duration))
        me.doframe(ref_time)
        me.doframe(obs_pos)
        hadec = me.direction('hadec',qa.time('%fs'%(duration/2))[0],dec)
        azel = me.measure(hadec,'azel')
        sm.setdata(msselect='SCAN_NUMBER==%d'%scan)
        start_time += scan_length
        scan += 1
    if noise: 
        sm.setnoise(mode='simplenoise',simplenoise=noise)
    sm.done()
    return msname
#makems(pos='meerkat.txt',tel='MeerKAT',label='MeerKAT64',pos_type='ascii',nchan=10,hours=8,dtime=60,start_time=-2)
