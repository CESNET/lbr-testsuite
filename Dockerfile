FROM oraclelinux:8

# http://bugs.python.org/issue19846
# > At the moment, setting "LANG=C" on a Linux system *fundamentally breaks Python 3*, and that's not OK.
ENV LANG en_US.UTF-8

COPY Pipfile Pipfile.lock /tmp/
RUN yum install -y python3
RUN yum clean all
RUN python3 -m pip install pipenv && cd /tmp && pipenv install --dev --system --deploy
