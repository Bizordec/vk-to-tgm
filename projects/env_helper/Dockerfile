FROM python:3.11.7-alpine3.19 AS build-stage

WORKDIR /code

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    VIRTUAL_ENV=/venv

RUN pip install poetry==1.8.3

COPY ./pyproject.toml ./poetry.lock* ./
RUN python -m venv $VIRTUAL_ENV \
    && poetry install --no-root --without=dev --no-interaction --no-ansi


FROM python:3.11.7-alpine3.19

WORKDIR /code

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH"

COPY --from=build-stage /venv /venv
COPY ./app ./app

CMD [ "python3", "-m", "app.main" ]
