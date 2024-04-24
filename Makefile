# Set default goal to help
.DEFAULT_GOAL := help
.PHONY: help

## Command used to generate the makefile commands documentation
help: ## Command used to generate the makefile commands documentation
	@echo '--------- Commands ---------'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo '----------------------------'

test: ## Execute the unit tests
	pytest

format: ## Format the code
	ruff format

check: ## Check the code
	ruff check --fix
