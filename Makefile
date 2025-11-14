
.PHONY: env-helper tunnel compose compose-debug pre-commit
.INTERMEDIATE: pre-commit.pyz

.DEFAULT_GOAL := compose

PRECOMMIT_VERSION := 3.7.1

env-helper:
	mkdir -p out/
	if [ -f .env ]; then cp .env out/.env; fi
	docker build -t env_helper projects/env_helper
	docker run --rm -it -v "$(PWD)/out":/tmp/out env_helper
	cp out/.env .env
	rm -r out/

tunnel:
	$(MAKE) -C projects/cb_receiver tunnel ARGS="80 $(PWD)/.env"

compose:
	COMPOSE_PROFILES=http,with-pl docker compose -f docker-compose.yml up --build --remove-orphans $(ARGS)

compose-ssl:
	COMPOSE_PROFILES=https,acme,with-pl docker compose -f docker-compose.yml up --build --remove-orphans $(ARGS)

compose-debug:
	COMPOSE_PROFILES=http,with-pl docker compose -f docker-compose.yml -f docker-compose.debug.yml up --build --remove-orphans $(ARGS)

############

pre-commit.pyz:
	wget -O pre-commit.pyz "https://github.com/pre-commit/pre-commit/releases/download/v${PRECOMMIT_VERSION}/pre-commit-${PRECOMMIT_VERSION}.pyz"; \
	python3 pre-commit.pyz install; \
	python3 pre-commit.pyz install --hook-type commit-msg

pre-commit: pre-commit.pyz
