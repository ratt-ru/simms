#!/usr/bin/env python

import os
from distutils.core import setup

setup(name="simms",
    version="1.0.0",
    description="Empty MS creation tool",
    author_email="Sphesihle Makhathini <sphemakh@gmail.com>",
    url="https://github.com/sphemakh/simms",
    packages=["Simms"],
    requires=["casapy","pyrap","numpy"],
    scripts=["Simms/bin/" + i for i in os.listdir("Simms/bin")],
     )
