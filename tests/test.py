import subprocess
import sys
import os

message = """
Cannot find casapy in your system:

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
_run("casa", ['--help','--log2term','--nologger','--nogui','--help','-c','quit'], 
            message=message)

# Finally see if we can run simms
_run('simms', ['-T', 'kat-7', '-st', '8', '-dt', '10'])

print "Done! All is good"
