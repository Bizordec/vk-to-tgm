FROM python:3.10.12-bullseye as build-stage

WORKDIR /vk-to-tgm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VIRTUALENVS_IN_PROJECT=1

RUN pip install poetry==1.5.1

COPY ./pyproject.toml ./poetry.lock* /vk-to-tgm/
RUN poetry install --no-root --without=dev --no-interaction --no-ansi


FROM python:3.10.12-slim-bullseye

WORKDIR /vk-to-tgm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/vk-to-tgm/.venv/bin:$PATH"

COPY --from=build-stage /vk-to-tgm/.venv/ /vk-to-tgm/.venv

RUN mkdir logs/

COPY app/ ./app
COPY app/celeryconfig.py.example ./app/celeryconfig.py
COPY locale/ ./locale
COPY vtt-cli.sh functions.sh ./
