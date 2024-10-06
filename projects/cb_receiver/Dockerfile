FROM python:3.11.7-alpine3.19 AS build-stage

WORKDIR /code/projects/cb_receiver

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    VIRTUAL_ENV=/venv

RUN pip install poetry==1.8.3

# Using additional build context 'libs'
COPY --from=libs ./vtt_common /code/libs/vtt_common
COPY ./pyproject.toml ./poetry.lock* ./
RUN sed -i "s/\(develop\s*=\s*\)true/\1false/" poetry.lock \
    && python -m venv $VIRTUAL_ENV \
    && poetry install --no-root --without=dev --no-interaction --no-ansi


FROM python:3.11.7-alpine3.19

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
COPY ./app ./app

CMD [ "uvicorn", "app.main:app", "--host", "0.0.0.0" ]
