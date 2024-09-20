.SILENT:
.PHONY: venv run build-image run-container clean

.DEFAULT_GOAL := run

.venv/bin/activate: poetry.lock
	POETRY_VIRTUALENVS_IN_PROJECT=true env -u VIRTUAL_ENV poetry install --no-root; \
	\
	# Update timestamp for this target
	touch .venv/bin/activate

venv: .venv/bin/activate

run: .venv/bin/activate
	.venv/bin/python3 -m app.main

############

build-image:
	OLD_IMAGE_ID=$$(docker images env_helper -q); \
	\
	echo "Building a new image..."; \
	docker build -t env_helper $(OPTS) .; \
	\
	NEW_IMAGE_ID=$$(docker images env_helper -q); \
	if [ -n "$$OLD_IMAGE_ID" ] && [ "$$OLD_IMAGE_ID" != "$$NEW_IMAGE_ID" ]; then \
		echo "Removing an old image..."; \
		docker rmi $$OLD_IMAGE_ID; \
	fi

run-container:
	docker run --rm -it -v "$(PWD)/out":/tmp/out env_helper

############

clean:
	rm -rf .venv
