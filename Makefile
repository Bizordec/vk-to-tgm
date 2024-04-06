.SILENT:
.PHONY: env-helper tunnel compose-local pre-commit
.INTERMEDIATE: pre-commit.pyz

.DEFAULT_GOAL := compose-local

PRECOMMIT_VERSION := 3.6.0

env-helper:
	$(MAKE) -C projects/env_helper build-image run-container HOST_ENV_PATH="$(PWD)/.env"

tunnel:
	$(MAKE) -C projects/cb_receiver tunnel ARGS="8000 $(PWD)/.env"

compose-local:
	docker compose -f docker-compose.local.yml --profile with-pl up --build --remove-orphans

############

pre-commit.pyz:
	wget -O pre-commit.pyz "https://github.com/pre-commit/pre-commit/releases/download/v${PRECOMMIT_VERSION}/pre-commit-${PRECOMMIT_VERSION}.pyz"; \
	python3 pre-commit.pyz install; \
	python3 pre-commit.pyz install --hook-type commit-msg

pre-commit: pre-commit.pyz
