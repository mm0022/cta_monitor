.PHONY: build bump-version clean config-repository fmt test

build:
	poetry build

test:
	PYTHONPATH=./nexus_data_hub_sdk poetry run pytest -v

bump-version:
	./bin/bump-version.sh

config-repository:
	poetry config repositories.cyberx https://pypi.cyberx-ops.com

release: clean build config-repository pyproject.toml
	@# export POETRY_HTTP_BASIC_CYBERX_USERNAME=username
	@# export POETRY_HTTP_BASIC_CYBERX_PASSWORD=password
	PIP_DEFAULT_TIMEOUT=120 poetry publish -r cyberx

clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf dist
	rm -rf .data
	rm -rf tests/__pycache__
	rm -rf tests/.data

fmt:
	autopep8 --in-place --recursive .
