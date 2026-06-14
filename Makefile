PYTHON ?= python3
VENV ?= .venv
APP_NAME := Half Deaf Mastering Tool
APP_BUNDLE := dist/$(APP_NAME).app
APP_EXEC := $(APP_BUNDLE)/Contents/MacOS/$(APP_NAME)

.PHONY: help venv install run test clean

help:
	@echo "Safe Mastering Assistant - Make targets"
	@echo ""
	@echo "Quick start:"
	@echo "  1) make run      # creates .venv if missing, installs deps, launches app"
	@echo "  2) make test     # creates .venv if missing, installs deps, runs tests"
	@echo ""
	@echo "Other targets:"
	@echo "  make help        # show this message"
	@echo "  make venv        # create .venv only"
	@echo "  make install     # create .venv if needed and install deps"
	@echo "  make clean       # remove .venv"
	@echo ""
	@echo "If ffmpeg is missing on macOS: brew install ffmpeg"

venv:
	@command -v $(PYTHON) >/dev/null 2>&1 || (echo "Python not found: $(PYTHON). Try: make run PYTHON=python3" && exit 1)
	@if [ ! -d "$(VENV)" ]; then \
		set -e; \
		$(PYTHON) -m venv $(VENV); \
		echo "Created virtual environment at $(VENV)"; \
	else \
		echo "Using existing virtual environment at $(VENV)"; \
	fi

install: venv
	@test -x $(VENV)/bin/pip || (echo "Virtual environment is not valid. Remove $(VENV) and retry." && exit 1)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt
	@echo "If ffmpeg is missing on macOS, run: brew install ffmpeg"

run: install
	$(VENV)/bin/python setup.py py2app -A
	@test -x "$(APP_EXEC)" || (echo "Expected executable not found: $(APP_EXEC)" && exit 1)
	open "$(APP_BUNDLE)"

test: install
	$(VENV)/bin/pytest -q

clean:
	rm -rf $(VENV)
