# use 'uv' to manage virtual environment if available
UV := $(shell command -v uv)

.PHONY: dev test

# install the development dependencies
dev: pyproject.toml
	$(UV) pip install -e .[dev]

# run tests
test:
	pytest
