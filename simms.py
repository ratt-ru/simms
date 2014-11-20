#!/usr/bin/env python
import os
import sys
import subprocess
from argparse import ArgumentParser
import time
import tempfile
import numpy as np

# set simms directory
simms_path = os.path.realpath(__file__)
simms_path = os.path.dirname(simms_path)

def simms(msname=None,label=None,tel=None,pos=None,pos_type='casa',
          ra='0h0m0s',dec='-30d0m0s',synthesis=4,scan_length=4,dtime=10,freq0=700e6,
          dfreq=50e6,nchan=1,stokes='LL LR RL RR',start_time=-2,setlimits=False,
          elevation_limit=0,shadow_limit=0,outdir='.',nolog=False,
          coords='itrf',lon_lat=None,noup=False):
    """ Make simulated measurement set """

    if not isinstance(dtime,str):
        dtime = '%ds'%dtime

    #TODO(sphe) Make this more general; try to find most sensible unit in [kHz,MHz,GHz]
    if not isinstance(freq0,str):
        freq0 = '%dMHz'%(freq0*1e-6)
    if not isinstance(dfreq,str):
        dfreq = '%dMHz'%(dfreq*1e-6)

    if msname is None:
        dd,rem = dec.split('d')
        dd = float(dd) + float(rem.split('m')[0])/60
        dec_sign = '%s%d'%('m' if dd<0 else 'p',abs(dd))
        msname = '%s/%s_%s_%dh%s_%s%s_%dch.MS'%(outdir,label or tel,dec_sign,synthesis,dtime,freq0,dfreq,nchan)

    casa_script = tempfile.NamedTemporaryFile(suffix='.py')
    casa_script.write('# Auto Gen casapy script. From simms.py\n')
    casa_script.write('execfile("%s/casasm.py")\n'%simms_path)

    fmt = 'msname="%(msname)s", label="%(label)s", tel="%(tel)s", pos="%(pos)s", '\
          'pos_type="%(pos_type)s", ra="%(ra)s", dec="%(dec)s", synthesis=%(synthesis).4g, '\
          'scan_length=%(scan_length).4g, dtime="%(dtime)s", freq0="%(freq0)s", dfreq="%(dfreq)s", '\
          'nchan=%(nchan)d, stokes="%(stokes)s", start_time=%(start_time).4g, setlimits=%(setlimits)s, '\
          'elevation_limit=%(elevation_limit)f, shadow_limit=%(shadow_limit)f, '\
          'coords="%(coords)s",lon_lat=%(lon_lat)s, noup=%(noup)s'%locals()
    casa_script.write('makems(%s)\nexit'%fmt)
    casa_script.flush()

    tmpfile = casa_script.name
    process = subprocess.Popen(['casapy --nologger --log2term %s -c %s'%('--nologfile'\
                  if nolog else '--logfile log-simms.txt',repr(tmpfile))],
                  stderr=subprocess.PIPE if not isinstance(sys.stderr,file) else sys.stderr,
                  stdout=subprocess.PIPE if not isinstance(sys.stdout,file) else sys.stdout,
                  shell=True)

    if process.stdout or process.stderr:
        out,err = process.comunicate()
        sys.stdout.write(out)
        sys.stderr.write(err)
        out = None;
    else:
        process.wait()
    if process.returncode:
        print 'ERROR: simms.py returns errr code %d'%(process.returncode)
    else:
        print 'DONE: simms.py succeeded. MS is at %s'%msname

    casa_script.close()
    casa_log_time_stamp = "%d%02d%02d-%02d%02d"%(time.gmtime()[:5])
    os.system('rm -f ipython-%s*.log '%casa_log_time_stamp)
    return msname

if __name__=='__main__':

    for i, arg in enumerate(sys.argv):
        if (arg[0] == '-') and arg[1].isdigit(): sys.argv[i] = ' ' + arg
    parser = ArgumentParser(description='Uses the CASA simulate tool to create '
            'an empty measurement set. Requires either an antenna table (CASA table) '
            'or a list of ITRF or ENU positions. '  
            'A standard file should have the format:\n '
            'pos1 pos2 pos3* dish_diameter station mount.\n'
            'NOTE: In the case of ENU, the 3rd position (up) is not essential '
            'and may not be specified; indicate that your file doesn\'t have this '
            'dimension by enebaling the --noup (-nu) option.')

    add = parser.add_argument
    add('pos',help='Antenna positions')
    add('-t','--type',dest='type',default='casa',choices=['casa','ascii'],
            help='position list type : dafault is casa')
    add('-cs','--coord-sys',dest='coords',default='itrf',choices=['itrf','enu'],
            help='Only relevent when --type=ascii. Coordinate system of antenna positions.' 
                 ' :dafault is itrf')
    add('-lle','--lon-lat-elv',dest='lon_lat',
            help='Reference position of telescope. Comma '
                 'seperated longitude,lattitude and elevation [deg,deg,m]. '
                 'Elevation is not crucial, lon,lat should be enough. If not specified,' 
                 ' we\'ll try to get this info from the CASA database: No default')
    add('-nu','--noup',dest='noup',action='store_true',
            help='Enable this to indicate that your ENU file does not have an '
                 '\'up\' dimension: This is not the default' )
    add('-T','--tel',dest='tel',
            help='Telescope name : no default')
    add('-n','--name',dest='name',
            help='MS name. A name based on the observatoion will be generated otherwise.')
    add('-od','--outdir',dest='outdir',default='.',
            help='Directory in which to save the MS: default is working directory')
    add('-l','--label',dest='label',
            help='Label to add to the auto generated MS name (if --name is not given)')
    add('-ra','--ra',dest='ra',default='0h0m0s',
            help = 'Right Assention in hms : default is 0h0m0s')
    add('-dec','--dec',dest='dec',default='-30d0m0s',type=str,
            help='Declination in dms: default is -30d0m0s')
    add('-st','--synthesis-time',dest='synthesis',default=4,type=float,
            help='Synthesis time in hours: default is 4.0')
    add('-sl','--scan-length',dest='scan_length',default=4,type=float,
            help='Synthesis time in hours: default is 4.0')
    add('-dt','--dtime',dest='dtime',default=10,type=int,
            help='Integration time in seconds : default is 10s')
    add('-ih','--init-ha',dest='init_ha',default=np.nan,type=float,
            help='Initial hour angle for observation default is -ve[syntheis time]/2')
    add('-nc','--nchan',dest='nchan',default=1,type=int,
            help='Number of frequency channels : default is 1')
    add('-f0','--freq0',dest='freq0',default='700MHz',
            help='Start frequency. Specify as val[unit]. E.g 700MHz, not unit => Hz : default is 700MHz')
    add('-df','--dfreq',dest='dfreq',default='50MHz',
            help='Channel width. Specify as val[unit]. E.g 700MHz, not unit => Hz : default is 50MHz')
    add('-pl','--pol',dest='pol',default='LL LR RL RR',
            help='Polarization : default is LL LR RL RR')
    add('-stl','--set-limits',dest='set_limits',action='store_true',
            help='Set telescope limits; elevation and shadow limts : not the default')
    add('-el','--elevation-limit',dest='elevation_limit',type=float,default=0,
            help='Dish elevation limit. Will only be taken into account if --set-limits (-stl) is enabled : no default')
    add('-shl','--shadow-limit',dest='shadow_limit',type=float,default=0,
            help='Shadow limit. Will only be taken into account if --set-limits (-stl) is enabled : no default')
    add('-ng','--nolog',dest='nolog',action='store_true',
            help='Don\'t keep Log file : not the default')

    args = parser.parse_args()
    if not args.tel:
        parser.error('Telescope name (--tel ot -T) is required')
    if args.name:
        args.name = '"%s"'%(args.name)

    for item in 'freq0','dfreq':
        try: 
            setattr(args,item,float(getattr(args,item)))
        except ValueError:  "do nothing"

    if np.isnan(args.init_ha):
        setattr(args,init_ha,args.synthesis/2)

    simms(msname=args.name,label=args.label,tel=args.tel,pos=args.pos,
          pos_type=args.type,ra=args.ra,dec=args.dec,synthesis=args.synthesis,scan_length=args.scan_length,
          dtime=args.dtime,freq0=args.freq0,dfreq=args.dfreq,nchan=args.nchan,
          stokes=args.pol,start_time=args.init_ha,setlimits=args.set_limits,
          elevation_limit=args.elevation_limit,shadow_limit=args.shadow_limit,
          outdir=args.outdir,coords=args.coords,lon_lat=args.lon_lat,noup=args.noup)
