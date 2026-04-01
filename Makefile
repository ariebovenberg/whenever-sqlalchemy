.PHONY: init
init:
	pip install -U setuptools build
	pip install -e ".[dev]"

.PHONY: test
test:
	pytest tests/ -v

.PHONY: cov
cov:
	pytest tests/ --cov=whenever_sqlalchemy --cov-report=html --cov-report=term
	@echo "Coverage report: htmlcov/index.html"

.PHONY: format
format:
	black src/ tests/
	isort src/ tests/

.PHONY: typecheck
typecheck:
	mypy src/ tests/

.PHONY: lint
lint:
	flake8 src/ tests/

.PHONY: ci-lint
ci-lint: lint typecheck
	black --check src/ tests/
	isort --check src/ tests/
	python -m build --sdist
	twine check dist/*

.PHONY: build
build:
	python -m build

.PHONY: clean
clean:
	rm -rf build/ dist/ src/**/__pycache__ **/__pycache__ *.egg-info **/*.egg-info \
		.mypy_cache/ .pytest_cache/ htmlcov/ .coverage*
