
.PHONY: env-helper tunnel compose compose-debug prek

.DEFAULT_GOAL := compose

env-helper:
	mkdir -p out/
	if [ -f .env ]; then cp .env out/.env; fi
	docker build \
	  --build-context libs=libs \
	  -t env_helper \
	  -f projects/env_helper/Dockerfile \
	  projects/env_helper/
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

prek:
	uv tool install prek && \
	prek install && \
	prek install --hook-type commit-msg
