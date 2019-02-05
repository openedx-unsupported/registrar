FROM python:3.6
RUN apt-get update
RUN apt-get install python3-dev -y
ADD requirements /edx/app/registrar/requirements
ADD Makefile /edx/app/registrar
WORKDIR /edx/app/registrar
RUN make requirements
