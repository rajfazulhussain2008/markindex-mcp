.PHONY: install test clean run

install:
	pip install -e .[dev,youtube]

test:
	pytest tests/ -v

coverage:
	pytest tests/ --cov=markindex --cov-report=term-missing

clean:
	rm -rf __pycache__
	rm -rf markindex/__pycache__
	rm -rf markindex/core/__pycache__
	rm -rf markindex/tools/__pycache__
	rm -rf tests/__pycache__
	rm -rf .pytest_cache
	rm -rf data/*

run:
	python -m markindex
