.SHELLFLAGS := -ec
.SILENT:
.PHONY: venv run

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
	.venv/bin/python3 -m app.main

clean:
	rm -rf .venv
