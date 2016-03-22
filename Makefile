NAME    = $(shell cat bundle.json | sed -n 's/"name"//p' | tr -d '", :')
PROJECT = sanji-bundle-$(NAME)
VERSION = $(shell cat bundle.json | sed -n 's/"version"//p' | tr -d '", :')

PROJECT_VERSION=$(PROJECT)-$(VERSION)

ARCHIVE=$(CURDIR)/$(PROJECT)-$(VERSION).tar.gz

SANJI_VER=1.0

INSTALL_DIR=$(DESTDIR)/usr/lib/sanji-$(SANJI_VER)/$(NAME)

STAGING_DIR=$(CURDIR)/staging

PROJECT_STAGING_DIR=$(STAGING_DIR)/$(PROJECT_VERSION)

FILES= \
	bundle.json \
	index.py \
	LICENSE \
	Makefile \
	README.md \
	requirements.txt \
	dhcpd/__init__.py \
	data/dhcpd.json.factory

INSTALL_FILES=$(addprefix $(INSTALL_DIR)/,$(FILES))

STAGING_FILES=$(addprefix $(PROJECT_STAGING_DIR)/,$(FILES))

.PHONY: clean dist pylint test

all:

clean:
	rm -rf $(PROJECT)-*.tar.gz $(STAGING_DIR)

dist: $(ARCHIVE)

pylint:
	flake8 -v --exclude=.git,__init__.py .

test:
	nosetests --with-coverage --cover-erase --cover-package=dhcpd -v

$(ARCHIVE): $(STAGING_FILES)
	cd $(STAGING_DIR) && \
	tar zcf $@ $(PROJECT_VERSION)

$(PROJECT_STAGING_DIR)/%: %
	mkdir -p $(dir $@)
	cp -a $< $@

install: $(INSTALL_FILES)

$(INSTALL_DIR)/%: %
	mkdir -p $(dir $@)
	install $< $@

uninstall:
	-rm $(addprefix $(INSTALL_DIR)/,$(FILES))
