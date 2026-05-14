FROM ghcr.io/astral-sh/uv:python3.14-alpine3.23 AS build-stage

WORKDIR /code

ENV UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_HTTP_TIMEOUT=120 \
    UV_PROJECT_ENVIRONMENT=/venv

# Required for cryptg
RUN apk --no-cache add cargo

COPY pyproject.toml ./
COPY uv.lock ./
COPY libs ./libs/
COPY projects ./projects/

RUN uv sync --project projects/env_helper --locked --no-dev


FROM python:3.14.5-alpine3.23

ARG UID=1000
ARG GID=1000

WORKDIR /code

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH"

RUN addgroup -g $GID user \
    && adduser --shell /sbin/nologin --disabled-password \
    --no-create-home --uid $UID --ingroup user user \
    && mkdir /tmp/out && chown $UID:$GID /tmp/out

USER user

COPY --from=build-stage /venv /venv
COPY projects/env_helper/app ./app

ENTRYPOINT [ "python3", "-m", "app.main" ]
CMD [ "--env-file", "/tmp/out/.env" ]
