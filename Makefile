all: pylint test

pylint:
	flake8 -v --exclude=.git,__init__.py .
test:
	nosetests --with-coverage --cover-erase --cover-package=dhcpd -v

.PHONY: pylint test
