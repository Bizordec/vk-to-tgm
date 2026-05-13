.SILENT:
.PHONY: venv run build-image clean

.DEFAULT_GOAL := run

.venv/bin/activate: pyproject.toml uv.lock
	uv sync; \
	\
	# Update timestamp for this target
	touch .venv/bin/activate

venv: .venv/bin/activate

run: .venv/bin/activate
	.venv/bin/python3 -m app.main

############

build-image:
	OLD_IMAGE_ID=$$(docker images env_validator -q); \
	\
	echo "Building a new image..."; \
	docker build --build-context libs=../../libs -t env_validator $(OPTS) .; \
	\
	NEW_IMAGE_ID=$$(docker images env_validator -q); \
	if [ -n "$$OLD_IMAGE_ID" ] && [ "$$OLD_IMAGE_ID" != "$$NEW_IMAGE_ID" ]; then \
		echo "Removing an old image..."; \
		docker rmi $$OLD_IMAGE_ID; \
	fi

############

clean:
	rm -rf .venv
