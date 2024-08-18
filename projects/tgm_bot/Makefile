.SILENT:
.PHONY: venv run build-image clean

.DEFAULT_GOAL := run

.venv/bin/activate: poetry.lock
	POETRY_VIRTUALENVS_IN_PROJECT=true env -u VIRTUAL_ENV poetry install --no-root; \
	\
	# Update timestamp for this target
	touch .venv/bin/activate

venv: .venv/bin/activate

run: .venv/bin/activate
	.venv/bin/python3 -m app.main

update_locales:
	mkdir -p locales/
	pybabel extract app/ -o locales/base.pot
	pybabel update -i locales/base.pot -D tgm_bot -d locales/
	pybabel compile -D tgm_bot -d locales/

############

build-image:
	OLD_IMAGE_ID=$$(docker images tgm_bot -q); \
	\
	echo "Building a new image..."; \
	docker build -t tgm_bot $(OPTS) .; \
	\
	NEW_IMAGE_ID=$$(docker images tgm_bot -q); \
	if [ -n "$$OLD_IMAGE_ID" ] && [ "$$OLD_IMAGE_ID" != "$$NEW_IMAGE_ID" ]; then \
		echo "Removing an old image..."; \
		docker rmi $$OLD_IMAGE_ID; \
	fi

############

clean:
	rm -rf .venv
