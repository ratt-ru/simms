import os
import subprocess
import sys

message = """
Cannot find casapy in your system:

Installation instructions are at:
http://casa.nrao.edu/installlinux.shtml


Install it, then re-run the test.py

"""

# check if simms is installed
subprocess.check_call(["simms", "--help"])

# Finally see if we can run simms
subprocess.check_call(["simms", "-T", "kat-7", "-st", "8", "-dt", "10"])

print("Done! All is good")
