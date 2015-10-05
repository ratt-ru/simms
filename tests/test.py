import subprocess
import sys
import os

message = """
Cannot find casapy in your system. Find casapy 4.2.2 at:
https://svn.cv.nrao.edu/casa/linux_distro/old/casapy-42.2.30986-1-64b.tar.gz

Installation instructions are at:
http://casa.nrao.edu/installlinux.shtml


Install it, then re-run the test.py

"""

def _run(command, options, message=None, shell=True):
    """ execute things on the command line """

    cmd = " ".join([command]+options)
    print('running: %s'%cmd)
    process = subprocess.Popen(cmd,
                  stderr=subprocess.PIPE if not isinstance(sys.stderr, file) else sys.stderr,
                  stdout=subprocess.PIPE if not isinstance(sys.stdout, file) else sys.stdout,
                  shell=shell)
    if process.stdout or process.stderr:
        out,err = process.comunicate()
        sys.stdout.write(out)
        sys.stderr.write(err)
        out = None
    else:
        process.wait()
    if process.returncode:
            raise SystemExit('%s: returns errr code %d. \n %s'%(command, process.returncode, 
            message or ""))

# check if simms is installed
_run("simms", ["--help"], message="Something went wrong with the installation")

# check if casapy is installed
_run("casapy", ['--help','--log2term','--nologger','--nogui','--help','-c','quit'], 
            message=message)

# Finally see if we can run simms
from simms import simms
simms.create_empty_ms(msname="test.MS", tel="kat-7", pos="../simms/observatories/KAT7_ANTENNAS",
                      synthesis=0.5, dtime=60)

print "Done! All is good"
