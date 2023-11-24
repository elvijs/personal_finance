# A collection of convenience tools for running the typical tasks

install: install_deps
	pip install -e .

install_deps:
	pip install -r requirements.txt

static_checks:
	ruff check .


format:
	ruff format .


test:
	pytest tests


freeze_requirements:
	pip freeze | grep -v personal_finance.git > requirements.txt
