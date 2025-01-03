# use 'uv' to manage virtual environment if available
UV := $(shell command -v uv)

.PHONY: dev test

# install the development dependencies
dev: pyproject.toml
	$(UV) pip install -e .[dev]
	pre-commit install

# run tests
test:
	pytest

.PHONY: lint format ruff debug-statements mypy

# lint the code
lint: ruff debug-statements mypy

# reformat code
format:
	pre-commit run ruff-format --all-files
	pre-commit run end-of-file-fixer --all-files
	pre-commit run trailing-whitespace --all-files

# individual linting tools

ruff:
	pre-commit run ruff --all-files

debug-statements:
	pre-commit run debug-statements --all-files

mypy:
	pre-commit run mypy --all-files
