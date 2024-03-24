.SHELLFLAGS := -ec
.SILENT:
.PHONY: venv run build-image clean

.DEFAULT_GOAL := run

poetry.lock:
.venv/bin/activate: poetry.lock
	POETRY_VIRTUALENVS_IN_PROJECT=true env -u VIRTUAL_ENV poetry install --no-root; \
	\
	# Update timestamp for this target
	touch .venv/bin/activate

venv: .venv/bin/activate

run: .venv/bin/activate
	.venv/bin/python3 -m celery -A app.main worker -n worker-wall -Q vtt-wall -c 1 -l INFO

test: .venv/bin/activate
	.venv/bin/pytest --cov --cov-report=html tests/

update_locales:
	pybabel extract app/ -o locales/base.pot
	pybabel update -i locales/base.pot -D worker_wall -d locales/
	pybabel compile -D worker_wall -d locales/

############

build-image:
	OLD_IMAGE_ID=$$(docker images worker_wall -q); \
	\
	echo "Building a new image..."; \
	docker build -t worker_wall --build-context libs=../../libs $(OPTS) .; \
	\
	NEW_IMAGE_ID=$$(docker images worker_wall -q); \
	if [ -n "$$OLD_IMAGE_ID" ] && [ "$$OLD_IMAGE_ID" != "$$NEW_IMAGE_ID" ]; then \
		echo "Removing an old image..."; \
		docker rmi $$OLD_IMAGE_ID; \
	fi

clean:
	rm -rf .venv
