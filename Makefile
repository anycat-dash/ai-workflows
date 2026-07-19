.PHONY: install install-dev install-all install-plugin init venv check-python uninstall list clean distclean

VENV       := .venv
VENV_PY    := $(VENV)/bin/python
VENV_PIP   := $(VENV)/bin/python -m pip
VENV_CLI   := $(VENV)/bin/ai-workflows

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

$(VENV)/bin/activate: | check-python
	python3 -m venv $(VENV) || python3 -m venv --without-pip $(VENV)
	$(VENV_PY) -m ensurepip --upgrade 2>/dev/null || \
		( curl -sS https://bootstrap.pypa.io/get-pip.py | $(VENV_PY) )
	$(VENV_PIP) install --upgrade pip

venv: $(VENV)/bin/activate

install-dev: venv
	$(VENV_PIP) install -e .

install-all: install-dev
	$(VENV_CLI) install all

install-plugin: install-dev
	@if [ -z "$(PLUGIN)" ]; then echo "usage: make install-plugin PLUGIN=<name>"; exit 1; fi
	$(VENV_CLI) install $(PLUGIN)

install: install-all

init: install-dev
	$(VENV_PY) plugins/init/scripts/init.py $(ARGS)

list:
	@ls plugins/

uninstall:
	-$(VENV_CLI) uninstall all --rules
	-$(VENV_PIP) uninstall -y ai-workflows

clean:
	rm -rf build dist *.egg-info

distclean: clean
	rm -rf $(VENV)
