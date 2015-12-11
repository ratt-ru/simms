#!/usr/bin/env python


from setuptools import setup, find_packages
from simms import __version__


scripts = [
    "simms/bin/simms"
]


package_data = {'simms': [
    'observatories/*.txt',
    'observatories/*/*',
    'src/*',
    'config.json',
]}


requires = [
    "numpy",
    "python_casacore"
]


setup(name="simms",
      version=__version__,
      description="Empty MS creation tool",
      author="Sphesihle Makhathini",
      author_email="sphemakh@gmail.com",
      url="https://github.com/radio-astro/simms",
      packages=find_packages(),
      package_data=package_data,
      requires=requires,
      scripts=scripts,
      license="GPL2",
      classifiers=[],
)
