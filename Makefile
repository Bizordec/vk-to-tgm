.SHELLFLAGS := -ec
.SILENT:
.PHONY: pre-commit
.INTERMEDIATE: pre-commit.pyz

.DEFAULT_GOAL := pre-commit

PRECOMMIT_VERSION := 3.6.0

pre-commit.pyz:
	wget -O pre-commit.pyz "https://github.com/pre-commit/pre-commit/releases/download/v${PRECOMMIT_VERSION}/pre-commit-${PRECOMMIT_VERSION}.pyz"; \
	python3 pre-commit.pyz install; \
	python3 pre-commit.pyz install --hook-type commit-msg

pre-commit: pre-commit.pyz
