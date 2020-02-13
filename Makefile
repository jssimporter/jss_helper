CURDIR := $(shell pwd)
MUNKIPKG := /usr/local/bin/munkipkg
PKG_ROOT := $(CURDIR)/pkg/jss_helper/payload
PKG_BUILD := $(CURDIR)/pkg/jss_helper/build
PKG_VERSION := $(shell defaults read $(CURDIR)/pkg/jss_helper/build-info.plist version)

objects = $(PKG_ROOT)/Library/AutoPkg/JSSImporter/packaging \
	$(PKG_ROOT)/usr/local/bin/jss_helper \
	$(PKG_ROOT)/usr/local/bin/jss_helper_lib


default : $(PKG_BUILD)/jss_helper-$(PKG_VERSION).pkg
	@echo "Building jss_helper pkg"


$(PKG_BUILD)/jss_helper-$(PKG_VERSION).pkg: $(objects)
	cd $(CURDIR)/pkg && $(MUNKIPKG) jss_helper


$(PKG_ROOT)/Library/AutoPkg/JSSImporter/packaging:
	@echo "Installing packaging into JSSImporter support directory"
	#pip install --install-option="--prefix=$(PKG_ROOT)/Library/AutoPkg/JSSImporter/packaging" --ignore-installed packaging
	pip3 install --target "$(PKG_ROOT)/Library/AutoPkg/JSSImporter" --ignore-installed packaging


$(PKG_ROOT)/usr/local/bin/jss_helper:
	@echo "Copying jss_helper into /usr/local/bin"
	mkdir -p "$(PKG_ROOT)/usr/local/bin"
	cp "$(CURDIR)/jss_helper" "$(PKG_ROOT)/usr/local/bin/jss_helper"
	chmod 755 "$(PKG_ROOT)/usr/local/bin/jss_helper"


$(PKG_ROOT)/usr/local/bin/jss_helper_lib:
	@echo "Copying jss_helper_lib into /usr/local/bin"
	cp -Rf "$(CURDIR)/jss_helper_lib" "$(PKG_ROOT)/usr/local/bin/jss_helper_lib"

.PHONY : clean
clean :
	@echo "Cleaning up package root"
	rm "$(PKG_ROOT)/usr/local/bin/jss_helper" ||:
	rm -rf "$(PKG_ROOT)/usr/local/bin/jss_helper_lib" ||:
	rm $(CURDIR)/pkg/jss_helper/build/*.pkg ||:
