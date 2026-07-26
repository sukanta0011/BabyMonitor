UV := uv
PY := $(UV) run python3
PACMAN := main.py
SRC := src
DEB := pdb

install: .venv/.installed

.venv/.installed: uv.lock pyproject.toml
	$(UV) sync
	@touch $@

run: .venv/.installed
	$(PY) $(PACMAN) config.json

debug: .venv/.installed
	$(PY) -m $(DEB) $(PACMAN)

clean: .venv/.installed
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

fclean: clean
	rm -rf .venv

re: fclean install

lint: .venv/.installed
	$(UV) run flake8 $(SRC)
	$(UV) run mypy $(SRC) --warn-return-any \
		      --warn-unused-ignores \
		      --ignore-missing-imports \
		      --disallow-untyped-defs \
		      --check-untyped-defs

.PHONY: install run debug clean fclean lint re
