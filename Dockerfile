FROM python:3.8.13-slim as build-stage

RUN apt-get update && apt-get install -y git build-essential

WORKDIR /vk-to-tgm

ENV VIRTUAL_ENV=/vk-to-tgm/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install poetry==1.1.13 \
    && python -m venv $VIRTUAL_ENV

COPY ./pyproject.toml ./poetry.lock* /vk-to-tgm/
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes \
    && pip install --no-cache-dir -r requirements.txt


FROM python:3.8.13-slim

WORKDIR /vk-to-tgm

ENV VIRTUAL_ENV=/vk-to-tgm/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY --from=build-stage /vk-to-tgm/.venv/ $VIRTUAL_ENV

RUN mkdir logs/

COPY app/ ./app
COPY app/celeryconfig.py.example ./app/celeryconfig.py
COPY locale/ ./locale
COPY vtt-cli.sh functions.sh ./
