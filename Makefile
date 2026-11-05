APP := app

.PHONY: dev install check check-all format

dev:
	./den

install:
	uv sync --project $(APP)

format:
	uv run --project $(APP) ruff format $(APP)
	uv run --project $(APP) ruff check --fix $(APP)

check:
	uv run --project $(APP) ruff format --check $(APP)
	uv run --project $(APP) ruff check $(APP)
	uv run --project $(APP) ty check $(APP)/den $(APP)/tests
	uv run --project $(APP) pytest -q $(APP)/tests

check-all: check
	gitleaks git --redact --no-banner .
