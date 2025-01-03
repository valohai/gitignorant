.PHONY: dev test

# install the development dependencies
dev: pyproject.toml
	pip install -e .[dev]

# run tests
test:
	pytest
