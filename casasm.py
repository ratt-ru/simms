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
    return xyz


def makems(msname=None,label=None,tel='MeerKAT',pos=None,pos_type='CASA',
           fromknown=False,
           direction=[],
           synthesis=4,
           scan_length=0,dtime=10,
           freq0=700e6,dfreq=50e6,nchan=1,
           nbands=1,
           start_time=None,
           stokes='LL LR RL RR',
           noise=0,
           setlimits=False,
           elevation_limit=None,
           shadow_limit=None,
           outdir=None,
           coords='itrf',           
           lon_lat=None,
           date=None,
           noup=False):
    """ Creates an empty measurement set using CASA simulate (sm) tool. """

    # The price you pay for allowing both string and float values for the same options
    def toFloat(val):
        try: return float(val)
        except TypeError: return val

    # sanity check/correction
    if scan_length > synthesis or scan_length is 0:
        print 'SIMMS ## WARN: Scan length > synthesis time or its not set, setiing scan_length=syntheis'
        scan_length = synthesis
    start_time = toFloat(start_time) or -scan_length/2
 
    if not isinstance(dtime,str):
        dtime = '%ds'%dtime
 
    
    stokes = 'LL LR RL RR'
    if msname.lower().strip()=='none': 
        msname = None
    #TODO: DO The above check for all other variables whch do not have defaults
    if msname is None:
        msname = '%s_%dh%s.MS'%(label or tel,synthesis,dtime)
    if outdir not in [None,'None','.']:
        msname = '%s/%s'%(outdir,msname)

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

    sm.open(msname)

    if fromknown:
        sm.setknownconfig('ATCA6.0A')
    elif pos:
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
        sm.setconfig(telescopename=tel,
                     x=xx,
                     y=yy,
                     z=zz,
                     dishdiameter=dish_diam,
                     mount=mount[0],
                     coordsystem='global',
                     referencelocation=obs_pos)

    else:
        raise RuntimeError('Observatory name is not known, please provide antenna configuration') 
        
    ref_time = me.epoch('IAT',date or '2015/01/01')
    sm.setfeed(mode='perfect X Y')
   
    for i,(freq,df,nc) in enumerate( zip(freq0,dfreq,nchan) ): 
        sm.setspwindow(spwname = '%02d'%i,
                   freq = freq,
                   deltafreq = df,
                   freqresolution = df,
                   nchannels = nc,
                   stokes= stokes)


    nfields = len(direction)
    for fid,field in enumerate(direction):
        field = field.split(',')
        sm.setfield(sourcename='%02d'%fid,sourcedirection=me.direction(*field))

    sm.settimes(integrationtime = dtime,
                usehourangle = True,
                referencetime = ref_time)
    
    if setlimits:
        sm.setlimits(shadowlimit=shadow_limit,elevationlimit=elevation_limit)
    sm.setauto(autocorrwt=0.0)

    start_times = map(str,np.arange(start_time,synthesis+start_time,scan_length)*3600)
    stop_times = map(str,np.arange(start_time,synthesis+start_time,scan_length)*3600 + scan_length*3600)

    for ddid in range(nbands):
        for start,stop in zip(start_times,stop_times):
            for fid in range(nfields):
                sm.observe('%02d'%fid,'%02d'%ddid,
                               starttime=start,stoptime=stop)
                me.doframe(ref_time)
                me.doframe(obs_pos)

    if sm.done():
        print 'DONE: simms.py succeeded. MS is at %s'%msname
    else:
         raise RuntimeError('Failed to create MS. Look at the log file. '
                            'Double check you settings. If you feel this '
                            'is due a to bug, raise an issue on https://github.com/SpheMakh/simms')
    return msname
