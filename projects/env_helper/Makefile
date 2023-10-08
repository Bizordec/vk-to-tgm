.SHELLFLAGS := -ec
.SILENT:
.PHONY: venv run pre-commit

.DEFAULT_GOAL := run

PRECOMMIT_VERSION := 3.4.0

.venv/bin/activate: pyproject.toml
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

pre-commit:
	wget -O pre-commit.pyz "https://github.com/pre-commit/pre-commit/releases/download/v${PRECOMMIT_VERSION}/pre-commit-${PRECOMMIT_VERSION}.pyz"
	python3 pre-commit.pyz install
	python3 pre-commit.pyz install --hook-type commit-msg
	trap "rm -f pre-commit.pyz" EXIT

clean:
	rm -rf .venv
