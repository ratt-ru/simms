FROM radioastro/casa

MAINTAINER gijsmolenaar@gmail.com

RUN apt-get update && \
    apt-get install -y \
        python-pip \
        python-casacore \
        python-numpy \
        python-pyfits \
        && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ADD . /tmp/simms

RUN cd /tmp/simms && python setup.py install

CMD /usr/local/bin/simms
