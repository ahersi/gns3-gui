# Run tests inside a container
FROM ubuntu:yakkety

MAINTAINER GNS3 Team

#ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update
RUN apt-get install -y --force-yes python3.5 python3-pyqt5 python3-pip python3-pyqt5.qtsvg python3-pyqt5.qtwebsockets python3.5-dev xvfb
RUN apt-get clean


ADD dev-requirements.txt /dev-requirements.txt
ADD requirements.txt /requirements.txt
RUN pip3 install -r /dev-requirements.txt


ADD . /src

WORKDIR /src

CMD xvfb-run python3.5 -m pytest -vv
