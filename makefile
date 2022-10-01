THIS_FILE := $(lastword $(MAKEFILE_LIST))
.PHONY: \
deps \
run

run:
	python main.py

deps:
	pip install -r ./requirements.txt --user