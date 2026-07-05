PYTHON ?= python3
VENV ?= .venv

ifeq ($(OS),Windows_NT)
VENV_BIN := $(VENV)/Scripts
PIP := $(VENV_BIN)/pip.exe
PYTHON_BIN := $(VENV_BIN)/python.exe
PYTEST := $(VENV_BIN)/pytest.exe
FFMPEG_HINT := If ffmpeg is missing on Windows, run: winget install ffmpeg (or choco install ffmpeg)
else
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip
PYTHON_BIN := $(VENV_BIN)/python
PYTEST := $(VENV_BIN)/pytest
FFMPEG_HINT := If ffmpeg is missing on macOS, run: brew install ffmpeg
endif

.PHONY: help venv install run windows_run test clean release_metadata release_macos_dmg release_windows_installer audit_json

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
	@echo "  make windows_run # alias for make run"
	@echo "  make release_metadata         # write dist/release-metadata.json"
	@echo "  make release_macos_dmg        # build macOS app + dmg (macOS only)"
	@echo "  make release_windows_installer # build Windows installer exe (Windows only)"
	@echo "  make audit_json  # run pip-audit for requirements files and write JSON reports"
	@echo "  make clean       # remove .venv"
	@echo ""
	@echo "$(FFMPEG_HINT)"

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
	@test -x $(PIP) || (echo "Virtual environment is not valid. Remove $(VENV) and retry." && exit 1)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(FFMPEG_HINT)"

run: install
	$(PYTHON_BIN) run_app.py

windows_run: run

test: install
	PYTHONPATH=. $(PYTEST) -q

release_metadata: install
	$(PYTHON_BIN) scripts/release.py metadata

release_macos_dmg: install
	$(PYTHON_BIN) scripts/release.py macos-dmg

release_windows_installer: install
	$(PYTHON_BIN) scripts/release.py windows-installer

audit_json: venv
	@test -x $(PIP) || (echo "Virtual environment is not valid. Remove $(VENV) and retry." && exit 1)
	$(PIP) install --upgrade pip-audit
	$(PYTHON_BIN) -m pip_audit -r requirements.txt -f json -o pip-audit-requirements.json
	$(PYTHON_BIN) -m pip_audit -r requirements-build.txt -f json -o pip-audit-requirements-build.json
	@echo "Wrote pip-audit-requirements.json and pip-audit-requirements-build.json"

clean:
	rm -rf $(VENV)
