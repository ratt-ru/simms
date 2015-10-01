#!/usr/bin/env python

import os
from setuptools import setup

setup(name="simms",
    version="0.5.2",
    description="Empty MS creation tool",
    author="Sphesihle Makhathini",
    author_email="Sphesihle Makhathini <sphemakh@gmail.com>",
    url="https://github.com/sphemakh/simms",
    packages=["simms"],
    requires=["casapy","numpy"],
    scripts=["simms/bin/" + i for i in os.listdir("simms/bin")], 
    licence="This program should come with the GNU General Public Licence. "\
            "If not, find it at http://www.gnu.org/licenses/old-licenses/gpl-2.0-standalone.html",
    classifiers=[],
     )
