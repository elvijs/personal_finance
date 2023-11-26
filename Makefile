# A collection of convenience tools for running the typical tasks

transaction_viewer:
	streamlit run scripts/view_transactions.py


install: install_deps
	pip install -e .

install_deps:
	pip install -r requirements.txt


qa: format static_checks test


static_checks: lint type_check

type_check:
	mypy .

lint:
	ruff check .


lint_fix:
	ruff check --fix .


format:
	ruff format .


test:
	pytest tests


freeze_requirements:
	pip freeze | grep -v personal_finance.git > requirements.txt
