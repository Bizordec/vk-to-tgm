.SILENT:
.PHONY: venv run build-image run-container clean

.DEFAULT_GOAL := run

.venv/bin/activate: pyproject.toml ../../uv.lock
	UV_PROJECT_ENVIRONMENT=$$(pwd)/.venv uv sync --project .
	# Update timestamp for this target
	touch .venv/bin/activate

venv: .venv/bin/activate

run:
	.venv/bin/python3 -m app.main

test:
	.venv/bin/pytest --cov --cov-report=html tests/

############

build-image:
	OLD_IMAGE_ID=$$(docker images env_helper -q); \
	\
	echo "Building a new image..."; \
	docker build -t env_helper -f Dockerfile $(OPTS) ../..; \
	\
	NEW_IMAGE_ID=$$(docker images env_helper -q); \
	if [ -n "$$OLD_IMAGE_ID" ] && [ "$$OLD_IMAGE_ID" != "$$NEW_IMAGE_ID" ]; then \
		echo "Removing an old image..."; \
		docker rmi $$OLD_IMAGE_ID; \
	fi

run-container:
	mkdir -p out && docker run --rm -it -v "$(PWD)/out":/tmp/out env_helper

############

clean:
	rm -rf .venv
