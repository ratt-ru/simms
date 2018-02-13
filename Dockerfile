FROM stimela/casa:0.3.1
MAINTAINER <sphemakh@gmail.com>

ADD . /tmp/simms

RUN cd /tmp/simms && python setup.py install
ENTRYPOINT ["/usr/local/bin/simms"]
CMD ["--help"]
