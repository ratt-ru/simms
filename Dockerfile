FROM radioastro/casa:4.2

MAINTAINER gijsmolenaar@gmail.com

RUN apt-get update && \
    apt-get install -y \
        python-pip \
        python-casacore \
        python-numpy \
        && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ADD . /tmp/simms

RUN cd /tmp/simms && python setup.py install

ENTRYPOINT /usr/local/bin/simms
