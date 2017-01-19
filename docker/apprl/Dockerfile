FROM python:2.7
 ENV PYTHONUNBUFFERED 1
 # RUN mkdir /
 WORKDIR /
 RUN apt-get update && \
     apt-get install -y libmemcached-dev zlib1g-dev
 ADD etc/requirements.pip /
 RUN pip install -r requirements.pip
 ADD . /

