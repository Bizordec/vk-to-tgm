
.PHONY: env-helper tunnel compose compose-debug pre-commit
.INTERMEDIATE: pre-commit.pyz

.DEFAULT_GOAL := compose

PRECOMMIT_VERSION := 3.7.1

env-helper:
	# $(MAKE) -C projects/env_helper build-image run-container HOST_ENV_PATH="$(PWD)/.env-test"

	mkdir -p out/
	cp .env out/.env
	docker build -t env_helper projects/env_helper
	docker run --rm -it -v "$(PWD)/out":/tmp/out env_helper
	cp out/.env .env
	rm -r out/

tunnel:
	$(MAKE) -C projects/cb_receiver tunnel ARGS="80 $(PWD)/.env"

compose:
	docker compose -f docker-compose.yml --profile with-pl up --build --remove-orphans

compose-debug:
	docker compose -f docker-compose.yml -f docker-compose.debug.yml --profile with-pl up --build --remove-orphans

compose-ssl:
	docker compose -f docker-compose.yml -f docker-compose.ssl.yml --profile with-pl up --build --remove-orphans

############

pre-commit.pyz:
	wget -O pre-commit.pyz "https://github.com/pre-commit/pre-commit/releases/download/v${PRECOMMIT_VERSION}/pre-commit-${PRECOMMIT_VERSION}.pyz"; \
	python3 pre-commit.pyz install; \
	python3 pre-commit.pyz install --hook-type commit-msg

pre-commit: pre-commit.pyz
