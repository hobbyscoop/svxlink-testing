FROM ubuntu:22.04 as builder
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
       git cmake g++ make libsigc++-2.0-dev libgsm1-dev \
       libpopt-dev tcl-dev libgcrypt20-dev libspeex-dev \
       libasound2-dev alsa-utils vorbis-tools qtbase5-dev \
       qttools5-dev qttools5-dev-tools libopus-dev \
       librtlsdr-dev libjsoncpp-dev libcurl4-openssl-dev \
       curl sudo groff doxygen checkinstall && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY ./ /src/
WORKDIR /src/build
RUN cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_SYSCONFDIR=/etc \
          -DCMAKE_INSTALL_LOCALSTATEDIR=/var \
          -DCMAKE_BUILD_TYPE=Release /src/src
RUN make
RUN groupadd svxlink && useradd -g svxlink svxlink
RUN checkinstall -D -y --pkgname svxlink --pkgversion $(date +%Y%m%d) --pkglicense GPLv3 \
                 --addso --gzman

FROM ubuntu:22.04 as run
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
        libsigc++-2.0-0v5 libgsm1 \
        libpopt0 tcl libgcrypt20 libspeex1 \
        libasound2 alsa-utils vorbis-tools \
        libopus0 librtlsdr0 libjsoncpp25 \
        python3 python3-numpy \
        && \
    rm -rf /var/lib/apt/lists/*
COPY --from=builder /src/build/svxlink_*.deb /svxlink.deb
RUN dpkg -i /svxlink.deb
CMD ["svxlink"]
