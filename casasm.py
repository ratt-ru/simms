# create a sumulated measurement from given a list of itrf antenna position or an antenna table (Casa table)
# Sphesihle Makhathini sphemakh@gmail.com
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

def freq_unit(val):
    val = val/1e3
    if val>10e6:
        return 'GHz',1e9
    elif val>1e3:
        return 'MHz',1e6
    else: 
        return 'kHz',1e3

def makems(msname=None,label=None,tel='MeerKAT',pos=None,pos_type='CASA',
           ra='0h0m0s',dec='-30d0m0s',
           direction=[],
           synthesis=4,
           scan_length=4,dtime=10,
           freq0=700e6,dfreq=50e6,nchan=1,
           nbands=1,
           start_time=None,
           stokes='LL LR RL RR',
           noise=0,
           setlimits=False,
           elevation_limit=None,
           shadow_limit=None,
           outdir='.',
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
 
    # The price you pay for allowing both string and float values for the same otions
    def toFloat(val):
        try: return float(val)
        except ValueError: return val

    if nbands>1:
        if isinstance(freq0,str) and freq0.find(',')>0:
            freqs = freq0.split(',')
            freq0 = freqs[0]
        else:
            freq0,dfreq = toFloat(freq0),toFloat(dfreq)
            if isinstance(freq0,str):
                freq = qa.convertfreq(freq0)['value']/1e6
            else:
                freq = freq0/1e6
            if isinstance(dfreq,str):
                df = qa.convertfreq(dfreq)
            else:
                df = dfreq/1e6
            freqs = ['%.4gMHz'%f for f in np.arange(nbands)*(nchan*df) + freq]
            freq0 = freqs[0]

    freq0,dfreq = toFloat(freq0),toFloat(dfreq)
    if not isinstance(freq0,str):
        unit,mult = freq_unit(freq0)
        freq0 = '%.4g%s'%(freq0/mult,unit)
    if not isinstance(dfreq,str):
        unit,mult = freq_unit(dfreq)
        dfreq = '%.4g%s'%(dfreq/mult,unit)
    
    stokes = 'LL LR RL RR'
    if msname.lower().strip()=='none': 
        msname = None
    #TODO: DO The above check for all other variables whch do not have defaults
    if msname is None:
        #dd = int(qa.unit(dec)['value'])
        #dec_sign = '%s%d'%('m' if dd<0 else 'p',abs(dd))
        msname = '%s/%s_%dh%s_%s%s_%dch.MS'%(outdir,label or tel,synthesis,dtime,freq0,dfreq,nchan)

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
   
    for i in range(nbands): 
        sm.setspwindow(spwname = '%02d'%i,
                   freq = freqs[i] if nbands>1 else freq0,
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

    if direction in [None,[]]:
        direction = [me.direction('J2000',ra,dec )]
    for fid,field in enumerate(direction):
        sm.setfield(sourcename='%02d'%fid,sourcedirection=field)

    sm.settimes(integrationtime = dtime,
                usehourangle = True,
                referencetime = ref_time)
    
    if setlimits:
        sm.setlimits(shadowlimit=shadow_limit,elevationlimit=elevation_limit)
    sm.setauto(autocorrwt=0.0)
    _start_time = start_time
    for fid in range(len(direction)):
        for ddid in range(nbands):
            scan = 0
            start_time = _start_time
            end_time = start_time + synthesis
            while (start_time < end_time):
                duration = (scan_length + start_time)*3600
                sm.observe('%02d'%fid,'%02d'%ddid,
                           starttime='%ds'%(start_time*3600),
                           stoptime='%ds'%(duration))
                me.doframe(ref_time)
                me.doframe(obs_pos)
                #hadec = me.direction('hadec',qa.time('%fs'%(duration/2))[0],dec)
                #azel = me.measure(hadec,'azel')
                sm.setdata(msselect='SCAN_NUMBER==%d && DATA_DESC_ID==%d && FIELD_ID==%d'%(scan,ddid,fid))
                start_time += scan_length
                scan += 1
#        if noise: 
#            sm.setnoise(mode='simplenoise',simplenoise=noise)
    sm.done()
    print 'DONE: simms.py succeeded. MS is at %s'%msname
    return msname
#makems(pos='meerkat.txt',tel='MeerKAT',label='MeerKAT64',pos_type='ascii',nchan=10,hours=8,dtime=60,start_time=-2)
