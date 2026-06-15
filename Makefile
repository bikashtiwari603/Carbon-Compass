.PHONY: run test lint format clean

run:
	uvicorn main:app --host 0.0.0.0 --port 8080 --reload

test:
	pytest test_main.py -v --tb=short

lint:
	pylint app/ main.py
	flake8 app/ main.py

format:
	black app/ main.py test_main.py
	isort app/ main.py test_main.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
