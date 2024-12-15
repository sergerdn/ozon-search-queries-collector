.PHONY: info
.DEFAULT_GOAL := info

# Include environment variables from the development file
include .env.development
export

# Get Git details
GIT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
GIT_COMMIT := $(shell git rev-list -1 HEAD)
GIT_VERSION := $(shell git describe --tags --always)

# Default target to display project info
info:
	@echo "Branch: ${GIT_BRANCH}"
	@echo "Commit: ${GIT_COMMIT}"
	@echo "Version: ${GIT_VERSION}"

clean_pycache:
	@if directories=$$(find . -type d -name __pycache__); then \
		find . -type d -name __pycache__ -exec rm -rf {} +; \
	else \
		echo "No __pycache__ directories found."; \
	fi

clean:
	$(MAKE) clean_pycache

lint_fix:
	#PYTHONUTF8=1 docconvert --in-place --config docconvert_config.json --output google ozon_collector/ main.py
	docformatter --config pyproject.toml --black --in-place --recursive ozon_collector/ main.py || echo ""
	poetry run black ozon_collector/ main.py
	poetry run isort ozon_collector/ main.py
