.PHONY: install install-dev init venv check-python uninstall list clean distclean

VENV       := .venv
VENV_PY    := $(VENV)/bin/python
VENV_CLI   := $(VENV)/bin/ai-workflows

# Prefer uv when available (5-10x faster). Fall back to python -m pip.
UV         := $(shell command -v uv 2>/dev/null)
ifneq ($(UV),)
  VENV_PIP := uv pip install --python $(VENV_PY)
  VENV_UNINSTALL := uv pip uninstall --python $(VENV_PY)
  MK_VENV  := uv venv $(VENV)
else
  VENV_PIP := $(VENV_PY) -m pip install
  VENV_UNINSTALL := $(VENV_PY) -m pip uninstall
  MK_VENV  := python3 -m venv $(VENV) || python3 -m venv --without-pip $(VENV); \
              $(VENV_PY) -m ensurepip --upgrade 2>/dev/null || \
                ( curl -sS https://bootstrap.pypa.io/get-pip.py | $(VENV_PY) ); \
              $(VENV_PY) -m pip install --upgrade pip
endif

# Positional args after `install` (e.g. `make install pr-review` or `make install all dry-run`)
RAW_ARGS     := $(filter-out install init,$(MAKECMDGOALS))
DRY          := $(if $(filter dry-run,$(RAW_ARGS))$(filter 1 true yes,$(DRY_RUN)),--dry-run,)
INSTALL_ARGS := $(filter-out dry-run,$(RAW_ARGS))

check-python:
	@if ! command -v python3 >/dev/null 2>&1; then \
		echo "python3 not found — installing..."; \
		if [ "$$(uname)" = "Darwin" ]; then \
			command -v brew >/dev/null 2>&1 || { echo "error: install Homebrew from https://brew.sh"; exit 1; }; \
			brew install python3; \
		elif command -v apt-get >/dev/null 2>&1; then \
			sudo apt-get update && sudo apt-get install -y python3 python3-venv; \
		elif command -v dnf >/dev/null 2>&1; then \
			sudo dnf install -y python3; \
		else \
			echo "error: unsupported platform, install python3 manually"; exit 1; \
		fi; \
	fi
	@python3 --version

$(VENV)/bin/python: | check-python
	$(MK_VENV)

venv: $(VENV)/bin/python

install-dev: venv
	$(VENV_PIP) hatchling editables
	$(VENV_PIP) --no-build-isolation -e .

install: install-dev
	@if [ -z "$(INSTALL_ARGS)" ]; then \
		echo "usage: make install <plugin|all> [dry-run]"; \
		echo "       make install all"; \
		echo "       make install pr-review"; \
		echo "       make install pr-review orchestrator dry-run"; \
		exit 1; \
	fi
	$(VENV_CLI) install $(INSTALL_ARGS) $(DRY)

init: install-dev
	$(VENV_PY) plugins/init/scripts/init.py $(if $(DRY),--dry-run,)

list:
	@$(VENV_CLI) list 2>/dev/null || ls plugins/

uninstall:
	-$(VENV_CLI) uninstall all --rules
	-$(VENV_UNINSTALL) ai-workflows

clean:
	rm -rf build dist *.egg-info

distclean: clean
	rm -rf $(VENV)

# Swallow positional args passed after `install` so make doesn't error
# on "No rule to make target 'pr-review'". Only matches undefined targets.
%:
	@:
