FROM python:3.6

COPY requirements.txt /tmp/requirements.txt
RUN python3.6 -m pip install -r /tmp/requirements.txt
