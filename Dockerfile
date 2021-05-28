FROM python:3.6

COPY Pipfile Pipfile.lock /tmp/
RUN python3 -m pip install pipenv && cd /tmp && pipenv install --system --deploy
