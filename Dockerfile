# This is a docker image for webcam
# Author: Lianjie Cao

FROM ubuntu:16.04

# Define environment variables for proxy
#ENV http_proxy http://web-proxy.labs.hpecorp.net:8080
#ENV HTTP_PROXY http://web-proxy.labs.hpecorp.net:8080
#ENV https_proxy http://web-proxy.labs.hpecorp.net:8080
#ENV HTTPS_PROXY http://web-proxy.labs.hpecorp.net:8080
#ENV no_proxy localhost,192.168.1.0/24
#ENV NO_PROXY localhost,192.168.1.0/24

MAINTAINER Lianjie Cao
EXPOSE 8888

RUN echo 'Acquire::http::Proxy "http://web-proxy.labs.hpecorp.net:8080/";' > /etc/apt/apt.conf
RUN apt update
RUN apt install -y vim curl python python-pip tcpdump net-tools
RUN pip install --proxy http://web-proxy.labs.hpecorp.net:8080 requests bottle wsgiserver Pillow

COPY webcam.py /opt/
CMD python /opt/webcam.py
