FROM ubuntu:oracular

RUN apt-get update
RUN apt-get install -y wireguard vim neovim iproute2 net-tools iputils-ping

COPY --chmod=0755 ./slp.sh /usr/bin/slp.sh
