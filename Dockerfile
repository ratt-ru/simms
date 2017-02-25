FROM kernsuite/casa
MAINTAINER <sphemakh@gmail.com>

ADD . /tmp/simms

RUN cd /tmp/simms && python setup.py install

CMD /usr/local/bin/simms
