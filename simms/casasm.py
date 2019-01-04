# create a sumulated measurement from given a list of itrf antenna position or an antenna table (Casa table)
# Sphesihle Makhathini sphemakh@gmail.com
import os
import sys
import numpy as np
import math
import glob

DEG = 180/math.pi

def get_int_data(tab):
    """ Get inteferometer information from antenna table """

    x,y,z = tab.getcol('POSITION')
    dish_diam = tab.getcol('DISH_DIAMETER')
    station = tab.getcol('STATION')
    mount = tab.getcol('MOUNT')
    return  (x,y,z),dish_diam,station,mount


def wgs84_2xyz(pos_wgs84):
    """ convert wgs84 to itrf """
    
    pos_itrf = np.zeros(pos_wgs84.shape)
    for i,(x,y,z) in enumerate(pos_wgs84):
        p = me.position("wgs84", "%fdeg"%x, "%fdeg"%y, "%fm"%z)
        pos_itrf[i] = me.addxvalue( me.measure(p, "itrf"))["value"]

    return pos_itrf
    

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
    
    xyz = xyz0[np.newaxis,:] + enu.dot(xform)
    return xyz


def makems(msname=None,label=None,tel='MeerKAT',pos=None,pos_type='CASA',
           fromknown=False,
           direction=[],
           synthesis=4,
           scan_length=0,dtime=10,
           freq0=700e6,dfreq=50e6,nchan=1,
           nbands=1,
           start_time=None,
           stokes='RR RL LR LL',
           feed="perfect R L",
           noise=0,
           setlimits=False,
           elevation_limit=None,
           shadow_limit=None,
           outdir=None,
           coords='itrf',           
           lon_lat=None,
           date=None,
           noup=False,
           auto_corr=False,
           scan_lag=0):
    """ Creates an empty measurement set using CASA simulate (sm) tool. """


    if (lon_lat is None) and tel and tel.upper() not in [ item.upper() for item in me.obslist() ]:
        raise ValueError("Could not Find your telescope [%s] in the CASA Database. "\
            "Please double check the telescope name, or provide the location of "\
            "the telescope via lon_lat (or --lon-lat-elv)"%tel)

    # The price you pay for allowing both string and float values for the same options
    def toFloat(val):
        try: return float(val)
        except TypeError: return val


    if not isinstance(dtime,str):
        dtime = '%ds'%dtime
    
    if msname.lower().strip()=='none': 
        msname = None
    if msname is None:
        msname = '%s_%dh%s.MS'%(label or tel,synthesis,dtime)
    if outdir not in [None,'None','.']:
        msname = '%s/%s'%(outdir,msname)

    obs_pos = None
    lon,lat = None,None
    if lon_lat not in [None,"None"]:
        if isinstance(lon_lat,str):
            tmp = lon_lat.split(',')
            lon,lat = ['%sdeg'%i for i in tmp[:2]]
            if len(tmp)>2:
                el = tmp[2]+'m'
            else:
                el = '0m'
            obs_pos = me.position('wgs84',lon,lat,el)
    obs_pos = obs_pos or me.observatory(tel)
    me.doframe(obs_pos)

    sm.open(msname)

    if fromknown:
        sm.setknownconfig(tel)

    elif pos:
        if pos_type.lower() == 'casa':
            tb.open(pos)
            (xx,yy,zz),dish_diam,station,mount = get_int_data(tb)
            tb.close()
            coords = 'itrf'

        elif pos_type.lower() == 'ascii':
            zz = np.zeros(len(pos))
            if noup: 
                names = ['x','y','dd','station','mount']
                ncols = 5
            else:
                names = ['x','y','z','dd','station','mount']
                ncols = 6
            dtype = ['float']*ncols
            dtype[-2:] = ['|S20']*2

            pos = np.genfromtxt(pos,names=names,dtype=dtype,usecols=range(ncols))
            xx,yy,zz = pos['x'], pos['y'], zz if noup else pos['z']
            dish_diam,station,mount = pos['dd'],pos['station'],pos['mount']

        coord_sys = dict(itrf="global", enu="local", wgs84="longlat")

        sm.setconfig(telescopename=tel,
                     x=xx,
                     y=yy,
                     z=zz,
                     dishdiameter=dish_diam,
                     mount= list(mount),
                     coordsystem= coord_sys.get(coords,'global'),
                     antname = list(station),
                     referencelocation=obs_pos)
    else:
        raise RuntimeError('Observatory name is not known, please provide antenna configuration') 

    if shadow_limit or elevation_limit:
        sm.setlimits(shadowlimit=shadow_limit or 0,elevationlimit=elevation_limit or 0)
    sm.setauto(autocorrwt=1.0 if auto_corr else 0.0)
    sm.setfeed(mode=feed)

    # set date to today (start of observation) if not set by user
    # The actual start time will be set internally by CASA depending on when the field transits
    use_ha = False
    if date is None:
        td = time.gmtime()
        date = "UTC,{0:d}/{1:d}/{02:d}".format(td.tm_year, td.tm_mon, td.tm_mday)
        use_ha = True

    # set reference time
    epoch, date = date.split(",")
    reftime = me.epoch(epoch, date)
    me.doframe(reftime)
    sm.settimes(integrationtime = dtime,
                usehourangle = use_ha,
                referencetime = reftime)

    ndir = len(direction)
    if scan_length:
        scan_length = [ float(sl)*3600 for sl in scan_length ]
        nscans = len(scan_length)
    else:
        nscans = 0

    synthesis *= 3600
    if ndir>=1:
        # if scan legth is not set, set it to equal the synthesis time
        if nscans == 0:
            scan_length = [synthesis*1.0/ndir]*ndir
            nscans = ndir
        while ndir > nscans:
          scan_length.append(scan_length[-1])

    # Set spectral window information
    if nbands > 1 and len(freq0) >1:
        nbands = len(freq0)
    elif nbands > 1 and len(freq0)==1:
        _freq0 = me.frequency("rest", freq0[0])["m0"]["value"]
        _dfreq = me.frequency("rest", dfreq)["m0"]["value"]
        bw = _dfreq*nchan + _freq0
        for band in range(1, nbands):
            __freq0 = "{:.4f}MHz".format(_freq + band*bw)
            freq0.append(__freq0)
    else:
        nbands = len(freq0)

    while len(nchan) < nbands:
        nchan.append(nchan[-1])
    while len(dfreq) < nbands:
            dfreq.append(dfreq[-1])

    for i,(freq,df,nc) in enumerate( zip(freq0,dfreq,nchan) ):
        bname = '{0:02d}'.format(i)
        sm.setspwindow(spwname = bname,
               freq = freq,
               deltafreq = df,
               freqresolution = df,
               nchannels = nc,
               stokes= stokes)

        # Set field information
        start_time = 0.0
        for fid,field in enumerate(direction):
            field = field.split(",")
            fname = sourcename="{0:02d}".format(fid)
            sm.setfield(sourcename=fname,
                        sourcedirection=me.direction(*field))

            for sl in scan_length:
                stop_time = start_time + sl
                sm.observe('{:02d}'.format(fid), '{:02d}'.format(i),
                        starttime=start_time,stoptime=stop_time)
                start_time += sl

    me.doframe(reftime)
    me.doframe(obs_pos)

    if sm.done():
        print "Empty MS '{}' created".format(msname)
    else:
         raise RuntimeError('Failed to create MS. Look at the log file. '
                            'Double check you settings. If you feel this '
                            'is due a to bug, raise an issue on https://github.com/SpheMakh/simms')

    # Clear all flags if limits were not  set
    if not setlimits:
        tb.open(msname, nomodify=False)
        flags = tb.getcol("FLAG")
        if flags.sum() > 0:
            flags[...] = False
            tb.putcol("FLAG", flags)
        tb.close()


    if validate(msname):
        return msname
    else:
        os.system("rm -fr %s"%msname)


def validate(msname):

    # Run a few tests on the MS, see if its valid.
    print "Validating %s ..."%msname
    validated = False

    try:
        tb.open(msname)
        data = tb.getcell("DATA", 0)
        ddid = list(set( tb.getcol("DATA_DESC_ID", 0) ))
        fid = list(set( tb.getcol("FIELD_ID", 0) ))
        tb.close()

        if data is None:
            validated = False
        elif 0 not in ddid or 0 not in fid:
            validated = False
        else:
            validated = True
    except ValueError:
        # Clean up and exit
        for tabF in glob.glob("tab*"):
            if os.path.isdir(tabF) and os.path.getmtime(tabF)>t0:
                os.system("rm -fr %s"%tabF)
        
        return False
    
    if validated:
        print "MS validated"
        return True
    else:
        return False

