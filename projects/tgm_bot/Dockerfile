# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:python3.14-alpine3.23 AS build-stage

WORKDIR /code/projects/tgm_bot

ENV UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_HTTP_TIMEOUT=120 \
    UV_PROJECT_ENVIRONMENT=/venv

# Required for cryptg
RUN apk --no-cache add cargo

COPY --from=libs . /code/libs/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-editable


FROM python:3.14.6-alpine3.23

ARG UID=1000
ARG GID=1000

WORKDIR /code

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH"

RUN addgroup -g $GID user \
    && adduser --shell /sbin/nologin --disabled-password \
    --no-create-home --uid $UID --ingroup user user

USER user

COPY --from=build-stage /venv /venv
COPY app ./app/
COPY locales ./locales/

CMD [ "python", "-m", "app.main" ]
