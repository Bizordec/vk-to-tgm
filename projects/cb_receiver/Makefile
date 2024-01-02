.SHELLFLAGS := -ec
.SILENT:
.PHONY: venv run tunnel

.DEFAULT_GOAL := run

.venv/bin/activate: poetry.lock
	if ! [ -x "$$(command -v poetry)" ]; then \
		echo "Install Poetry and try again."; \
		exit 1; \
	fi

	if [ -n "$$VIRTUAL_ENV" ]; then \
		echo "Deactivate virtual environment by executing 'deactivate' and try again."; \
		exit 1; \
	fi

	POETRY_VIRTUALENVS_IN_PROJECT=true poetry install --no-root

	# Update timestamp for this target
	touch .venv/bin/activate

venv: .venv/bin/activate

run: .venv/bin/activate
	.venv/bin/python3 -m uvicorn app.main:app

############

tunnel/node_modules: tunnel/package-lock.json
	npm install --prefix ./tunnel/

	# Update timestamp for this target
	touch tunnel/node_modules

tunnel: tunnel/node_modules
	npm start --prefix ./tunnel/

############

clean:
	rm -rf .venv tunnel/node_modules/
