## Sphesihle Makhathini <sphemakh@gmail.com>

import os
import sys
import subprocess
import argparse
import time
import tempfile
import glob
import numpy as np
import json



# I want to replace error() in argparse.ArgumentParser class
# I do this so I can catch the exception raised when too few arguments
# are parsed. 
class ParserError(Exception): 
    pass
class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ParserError(message or 'Not enough Arguments')

# set simms directory
simms_path = os.path.realpath(__file__)
simms_path = os.path.dirname(simms_path)
execfile("%s/__init__.py"%simms_path)

# Communication functions
def info(string):
    t = "%d/%d/%d %d:%d:%d"%(time.localtime()[:6])
    print "%s ##INFO: %s"%(t,string)
def warn(string):
    t = "%d/%d/%d %d:%d:%d"%(time.localtime()[:6])
    print "%s ##WARNING: %s"%(t,string)

def abort(string,exception=SystemExit):
    t = "%d/%d/%d %d:%d:%d"%(time.localtime()[:6])
    raise exception("%s ##ABORTING: %s"%(t,string))

class CasapyError(Exception):
    pass


def create_empty_ms(msname=None,label=None,tel=None,pos=None,pos_type='casa',
          ra='0h0m0s',dec='-30d0m0s',synthesis=4,scan_length=4,dtime=10,freq0=700e6,
          dfreq=50e6,nchan=1,stokes='XX XY YX YY',start_time=-2,setlimits=False,
          elevation_limit=0,shadow_limit=0,outdir=None,nolog=False,
          coords='itrf',lon_lat=None,noup=False,nbands=1,direction=[],date=None,
          fromknown=False,feed="perfect X Y"):

    """ 
Uses the CASA simulate tool to create an empty measurement set. Requires
either an antenna table (CASA table) or a list of ITRF or ENU positions. 

msname: MS name
tel: Telescope name (This name must be in the CASA Database (check in me.obslist() in casapy)
     If its not there, then you will need to specify the telescope coordinates via "lon_lat"
pos: Antenna positions. This can either a CASA table or an ASCII file. 
     (see simms --help for more on using an ascii file)
pos_type: Antenna position type. Choices are (casa, ascii)
coords: This is only applicable if you are using an ASCII file. Choices are (itrf, enu)
synthesis: Synthesis time in hours
dtime: Integration time in seconds
freq0: Start frequency 
dfreq: Channel width
nbands: Number of frequency bands
**kw: extra keyword arguments.

A standard file should have the format: pos1 pos2 pos3* dish_diameter station
mount. NOTE: In the case of ENU, the 3rd position (up) is not essential and
may not be specified; indicate that your file doesn't have this dimension by
enebaling the --noup (-nu) option.
    """

    def toList(value, nchan=False):
        if isinstance(value, str):
            string = value.split(",")
            if len(string)>1:
                return map(int, string) if nchan else string
            else:
                return int(value) if nchan else value
        elif isinstance(value, (int, float)):
            return value if nchan else "%fMHz"%(value/1e6)
            
    dfreq = toList(dfreq)
    freq0 = toList(freq0)
    nchan = toList(nchan, nchan=True)

    if nbands==1 and isinstance(nchan, (list, tuple)):
        nbands = len(nchan)
        
    if nbands>1:
        if isinstance(freq0, str):
            freq0 = [freq0]*nbands
        if isinstance(dfreq, str):
            dfreq = [dfreq]*nbands
        if isinstance(nchan, int):
            nchan = [nchan]*nbands
    else:
         freq0 = [freq0]
         dfreq = [dfreq]
         nchan = [nchan]

    if direction in [None,[],()]:
        direction = ','.join(['J2000',ra,dec])
    if isinstance(direction,str):
        direction = [direction]

    if date is None:
        date = ['UTC,%d/%d/%d'%(time.localtime()[:3])]

    if msname is None:
        msname = '%s_%dh%ss.MS'%(label or tel,synthesis,dtime)
    if outdir not in [None,'.']:
        msname = '%s/%s'%(outdir,msname)
        outdir = None

    cdir = os.path.realpath('.')


    message = "Having Trouble accessing the MS. Something went wrong while creating the MS, please check the logs.\n"\
              "If you believe this is due to a bug in simms, please notify me via "\
              "https://github.com/SpheMakh/simms/issues/new"

    casa_script = tempfile.NamedTemporaryFile(suffix='.py')
    casa_script.write("""
# Auto Gen casapy script. From simms.py
import os
os.chdir('%s')
execfile('%s/casasm.py')
"""%(cdir,simms_path) )

    if isinstance(scan_length, (str, int, float)):
        if isinstance(scan_length, str):
            scan_length = map(float, scan_length.split(","))
        else:
            scan_length = [scan_length]

    scan_length = scan_length or [0]
    if len(scan_length)==1:
        if scan_length[0] == 0:
            scan_length = [synthesis]
        else:
            nscans = int( np.ceil( synthesis/float(scan_length[0]) ) )
            scan_length = scan_length*nscans

    fmt = 'msname="%(msname)s", label="%(label)s", tel="%(tel)s", pos="%(pos)s", '\
          'pos_type="%(pos_type)s", synthesis=%(synthesis).4g, '\
          'scan_length=%(scan_length)s, dtime="%(dtime)s", freq0=%(freq0)s, dfreq=%(dfreq)s, '\
          'nchan=%(nchan)s, stokes="%(stokes)s", start_time=%(start_time)s, setlimits=%(setlimits)s, '\
          'elevation_limit=%(elevation_limit)f, shadow_limit=%(shadow_limit)f, '\
          'coords="%(coords)s",lon_lat="%(lon_lat)s", noup=%(noup)s, nbands=%(nbands)d, '\
          'direction=%(direction)s, outdir="%(outdir)s",date=%(date)s,fromknown=%(fromknown)s, '\
          'feed="%(feed)s"'%locals()
    casa_script.write('makems(%s)\nexit'%fmt)
    casa_script.flush()

    tmpfile = casa_script.name
    t0 = time.time()
    logfile = 'log-simms.txt'
    command = ['casapy', '--nologger', '--log2term', 
                  '%s'%('--nologfile' if nolog else '--logfile %s'%logfile),'-c',tmpfile]
    tmpdir = tempfile.mkdtemp(dir='.')

    if os.path.exists(msname):
        os.system("rm -fr %s"%msname)

    t0 = time.time() 

    process = subprocess.Popen("cd %s && "%tmpdir+" ".join(command),
                  stderr=subprocess.PIPE if not isinstance(sys.stderr,file) else sys.stderr,
                  stdout=subprocess.PIPE if not isinstance(sys.stdout,file) else sys.stdout,
                  shell=True)

    if process.stdout or process.stderr:
        out,err = process.communicate()
        sys.stdout.write(out)
        sys.stderr.write(err)
        out = None
    else:
        process.wait()
    if process.returncode:
        print 'ERROR: simms.py returns errr code %d. %s'%(process.returncode, message)

    casa_script.close()
    os.system('mv %s/%s . && rm -fr %s'%(tmpdir,logfile,tmpdir) )
    for log in glob.glob("ipython-*.log"):
        if os.path.getmtime(log)>t0:
            os.system("rm -f %s"%log)
    
    if nolog:
        for log in glob.glob("casapy*.log"):
            if os.path.getmtime(log)>t0:
                os.system("rm -f %s"%log)

    # Log the simms command that invoked simms and add a time stamp
    if not nolog:
        with open(logfile,'a') as std:
            ts = '%d/%d/%d  %d:%d:%d'%(time.localtime()[:6])
            ran = " ".join(map(str,sys.argv))
            std.write('\n %s ::: %s\n%s\n'%(ts," ".join(command),ran))

    if os.path.exists(msname):
        info("simms succeeded")
    else:
        raise CasapyError(message)

# Add this for backwards compatibilty.
simms = create_empty_ms

def main():

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
    add("-v","--version", action='version',version='%s version %s'%(parser.prog,__version__))
    add('-ukc','--use-known-config',dest='knownconfig',action='store_true',
            help='Use known antenna configuration. For some reason sm.setknownconfig() '
            'is not working. So this option does not work as yet.')
    add('pos',help='Antenna positions', nargs='?')
    add('-t','--type',dest='type',default='casa',choices=['casa','ascii'],
            help='position list type : dafault is casa')
    add('-cs','--coord-sys',dest='coords',default='itrf',choices=['itrf','enu','wgs84'],
            help='Only relevent when --type=ascii. Coordinate system of antenna positions.' 
                 ' :dafault is itrf')
    add('-lle','--lon-lat-elv',dest='lon_lat',
            help='Reference position of telescope. Comma '
                 'seperated longitude,lattitude and elevation [deg,deg,m]. '
                 'Elevation is not crucial, lon,lat should be enough. If not specified,' 
                 ' we\'ll try to get this info from the CASA database '
                 '(assuming that your observatory is known to CASA; --tel, -T): No default')
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
    add('-dir','--direction',dest='direction',action='append',default=[],
            help='Pointing direction. Example J2000,0h0m0s,-30d0m0d. Option '
                 '--direction may be specified multiple times for multiple pointings')
    add('-ra','--ra',dest='ra',default='0h0m0s',
            help = 'Right Assention in hms or val[unit] : default is 0h0m0s')
    add('-dec','--dec',dest='dec',default='-30d0m0s',type=str,
            help='Declination in dms or val[unit]: default is -30d0m0s')
    add('-st','--synthesis-time',dest='synthesis',default=4,type=float,
            help='Synthesis time in hours: default is 4.0')
    add('-sl','--scan-length',dest='scan_length',type=str,
            help='Synthesis time in hours: default is the sysntheis time')
    add('-dt','--dtime',dest='dtime',default=10,type=int,
            help='Integration time in seconds : default is 10s')
    add('-ih','--init-ha',dest='init_ha',default=None,
            help='Initial hour angle for observation. If not specified '
                 'we use -[scan_length/2]')
    add('-nc','--nchan',dest='nchan',default='1',
            help='Number of frequency channels. Specify as comma separated list ' 
                 ' (for multiple subbands); see also --freq0, --dfreq: default is 1')
    add('-f0','--freq0',dest='freq0',default='700MHz',
            help='Start frequency. Specify as val[unit]. E.g 700MHz, not unit => Hz .'
                 ' Use a comma seperated list for multiple start frequencies ' 
                 '(for multiple subbands); see also --nchan, --dfreq: default is 700MHz')
    add('-df','--dfreq',dest='dfreq',default='50MHz',
            help='Channel width. Specify as val[unit]. E.g 700MHz, not unit => Hz '
                 'Use a comma separated list of channel widths (for multiple subbands);'
                 ' see also --nchan, --freq0 : default is 50MHz')
    add('-nb','--nband',dest='nband',default=1,type=int,
            help='Number of subbands : default is 1')
    add('-pl','--pol',dest='pol',default='XX XY YX YY',
            help='Polarization : default is XX XY YX YY')
    add('-feed','--feed',dest='feed',default='perfect X Y',
            help='Polarization : default is "perfect X Y" ')
    add('-date','--date',dest='date',metavar="EPOCH,yyyy/mm/dd[/h:m:s]",action="append",default=[],
            help='Date of observation. Example "UTC,2014/05/26" or "UTC,2014/05/26/12:12:12" : default is today')
    add('-stl','--set-limits',dest='set_limits',action='store_true',
            help='Set telescope limits; elevation and shadow limts : not the default')
    add('-el','--elevation-limit',dest='elevation_limit',type=float,default=0,
            help='Dish elevation limit. Will only be taken into account if --set-limits (-stl) is enabled : no default')
    add('-shl','--shadow-limit',dest='shadow_limit',type=float,default=0,
            help='Shadow limit. Will only be taken into account if --set-limits (-stl) is enabled : no default')
    add('-ng','--nolog',dest='nolog',action='store_true',
            help='Don\'t keep Log file : not the default')
    add('-jc','--json-config',dest='config',
            help='Json config file : No default')

    try:
        args = parser.parse_args()
    except ParserError: 
        args = parser.parse_args(args=sys.argv)
        print args

    if args.config:
        with open(args.config) as conf:
            jdict = json.load(conf)

        for key, val in jdict.iteritems():
            if isinstance(val, unicode):
                jdict[key] = str(val)

        simms(**jdict)

    else:
        

        if (not args.tel) and (not args.lon_lat):
            parser.error('Either the telescope name (--tel/-T) or Telescope coordinate (-lle/--lon-lat )is required')

        simms(msname=args.name,label=args.label,tel=args.tel,pos=args.pos,feed=args.feed,
              pos_type=args.type,ra=args.ra,dec=args.dec,synthesis=args.synthesis,scan_length=args.scan_length,
              dtime=args.dtime,freq0=args.freq0,dfreq=args.dfreq,nchan=args.nchan,
              stokes=args.pol,start_time=args.init_ha,setlimits=args.set_limits,
              elevation_limit=args.elevation_limit,shadow_limit=args.shadow_limit,
              outdir=args.outdir,coords=args.coords,lon_lat=args.lon_lat,noup=args.noup,
              direction=args.direction,nbands=args.nband,date=args.date,fromknown=args.knownconfig)
