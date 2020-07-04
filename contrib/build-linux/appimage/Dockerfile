FROM ubuntu:16.04

ENV LC_ALL=C.UTF-8 LANG=C.UTF-8

RUN apt-get update -q && \
    apt-get install -qy \
        git \
        wget \
        make \
        autotools-dev \
        autoconf \
        libtool \
        xz-utils \
        libssl-dev \
        zlib1g-dev \
        libffi6 \
        libffi-dev \
        libncurses5-dev \
        libsqlite3-dev \
        libusb-1.0-0-dev \
        libudev-dev \
        gettext \
        libzbar0  \
        faketime \
        && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get autoremove -y && \
    apt-get clean
