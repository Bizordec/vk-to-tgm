.SILENT:
.PHONY: venv run build-image tunnel clean

.DEFAULT_GOAL := run

.venv/bin/activate: poetry.lock
	POETRY_VIRTUALENVS_IN_PROJECT=true env -u VIRTUAL_ENV poetry install --no-root; \
	\
	# Update timestamp for this target
	touch .venv/bin/activate

venv: .venv/bin/activate

run: .venv/bin/activate
	.venv/bin/python3 -m uvicorn app.main:app

############

build-image:
	OLD_IMAGE_ID=$$(docker images cb_receiver -q); \
	\
	echo "Building a new image..."; \
	docker build -t cb_receiver --build-context libs=../../libs $(OPTS) .
	\
	NEW_IMAGE_ID=$$(docker images env_helper -q); \
	if [ -n "$$OLD_IMAGE_ID" ] && [ "$$OLD_IMAGE_ID" != "$$NEW_IMAGE_ID" ]; then \
		echo "Removing an old image..."; \
		docker rmi $$OLD_IMAGE_ID; \
	fi

############

tunnel/node_modules: tunnel/package-lock.json
	npm install --prefix ./tunnel/

	# Update timestamp for this target
	touch tunnel/node_modules

tunnel: tunnel/node_modules
	npm start --prefix ./tunnel/ $(ARGS)

############

clean:
	rm -rf .venv tunnel/node_modules/
