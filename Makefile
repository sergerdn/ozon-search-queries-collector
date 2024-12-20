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

lint:
	poetry check
	poetry run mypy ozon_collector/ main.py
	poetry run flake8 ozon_collector/ main.py

check_env:
	@if [ -z "$(BROWSER_PROFILE_STORAGE_DIR)" ]; then \
        echo "Error: BROWSER_PROFILE_STORAGE_DIR is not set!"; \
        exit 1; \
    fi

dev_scrapy_crawl: check_env
	poetry run scrapy crawl ozon_data_query_spider -a initial_query_keyword="" \
		-o items.json -a parse_in_depth=True -a query_popularity_threshold=0 \
		--logfile ozon_data_query_spider.log
