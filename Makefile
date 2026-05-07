# PhotoOrganizer — orchestration des tâches courantes
#
# Cibles principales :
#   make install        installe les deps + outils dev
#   make lint           ruff + bandit
#   make test           tests rapides
#   make test-all       tests + slow + benchmarks
#   make bench          uniquement les benchmarks
#   make build-debug    exe debug
#   make build-release  exe release windowed
#   make build          debug + release
#   make clean          supprime build artifacts
#   make all            install + lint + test + build

PYTHON  ?= python
SRC     := src
TESTS   := tests

.PHONY: help install lint test test-all bench build build-debug build-release \
        build-light clean all

help:
	@echo "Cibles : install lint test test-all bench build build-debug build-release build-light clean all"

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e ".[dev]"
	$(PYTHON) -m pip install ruff vulture bandit pytest pytest-cov pytest-benchmark pyinstaller

lint:
	$(PYTHON) -m ruff check $(SRC) main.py build.py --select=E,F,W,B,S || true
	$(PYTHON) -m bandit -r $(SRC) -ll || true

test:
	$(PYTHON) -m pytest $(TESTS) -m "not slow" --cov=$(SRC) --cov-report=term-missing

test-all:
	$(PYTHON) -m pytest $(TESTS) --cov=$(SRC) --cov-report=term-missing --cov-report=html

bench:
	$(PYTHON) -m pytest $(TESTS)/perf/ --benchmark-only

build-debug:
	$(PYTHON) build.py --debug

build-release:
	$(PYTHON) build.py

build-light:
	$(PYTHON) build.py --light

build: build-debug build-release

clean:
	rm -rf build dist *.spec __pycache__ .pytest_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

all: install lint test build
