simms
=====

Creates simulated measurement sets using the the CASA simulate tool. 

Requires
-----
CASA http://casa.nrao.edu/casa_obtaining.shtml and numpy

./simms.py --help should be helpful ;)

Install 
---
`$ git clone https://github.com/SpheMakh/simms `  
then add the following to your .bashrc file:   
`export PATH=$PATH:path_to_simms_dir/bin`  
`export PYTHONPATH=$PYTHONPATH:path_to_simms_dir`

source .bashrc and you are good to go.

Examples
------
./simms.py -T meerkat -t casa -l test -dec -30d0m0s -ra 0h0m0s -st 8 -sl 4 -dt 60 -ih -2 -f0 700MHz -nc 4 -df 10MHz MeerKAT64_ANTENNAS

Creates an empty MS at 700MHz with 4 10MHz channels, the observtion is 8hrs long with 4 hours scans and a 60s integrations time. The MS is created from the MeerKAT64 CASA antenna table (which must be provided by the user)
