# Makefile for generating documentation

# Man page sources
MAN1_SOURCES = docs/man/fplaunch-manage.1 \
               docs/man/fplaunch-generate.1 \
               docs/man/fplaunch-setup-systemd.1 \
               docs/man/fplaunch-cleanup.1

MAN7_SOURCES = docs/man/fplaunchwrapper.7

# Info page output
INFO_DIR = docs/info
INFO_PAGES = $(INFO_DIR)/fplaunchwrapper.info

# Output directories
MAN_DIR = docs/man
BUILD_DIR = build

.PHONY: all man info clean install-man install-info

all: man info

# Build man pages (just copy, they're already in roff format)
man: $(MAN1_SOURCES) $(MAN7_SOURCES)
	@echo "Man pages ready in $(MAN_DIR)"

# Build info pages from man pages
info: $(INFO_PAGES)

$(INFO_DIR)/fplaunchwrapper.info: $(MAN1_SOURCES) $(MAN7_SOURCES) docs/info/fplaunchwrapper.texi
	@mkdir -p $(INFO_DIR)
	makeinfo --output=$@ docs/info/fplaunchwrapper.texi

# Install man pages (for testing)
install-man: man
	@echo "Installing man pages..."
	install -d $(DESTDIR)/usr/share/man/man1
	install -d $(DESTDIR)/usr/share/man/man7
	install -m 644 $(MAN1_SOURCES) $(DESTDIR)/usr/share/man/man1/
	install -m 644 $(MAN7_SOURCES) $(DESTDIR)/usr/share/man/man7/
	@echo "Man pages installed"

# Install info pages
install-info: info
	@echo "Installing info pages..."
	install -d $(DESTDIR)/usr/share/info
	install -m 644 $(INFO_PAGES) $(DESTDIR)/usr/share/info/
	@echo "Info pages installed"

# Test man pages locally (view without installing)
test-man:
	@echo "Testing man pages (use 'q' to quit)..."
	@for page in $(MAN1_SOURCES) $(MAN7_SOURCES); do \
		echo "Viewing $$page..."; \
		man -l $$page; \
	done

# Clean generated files
clean:
	rm -rf $(INFO_DIR)/*.info $(BUILD_DIR)

# Help target
help:
	@echo "Available targets:"
	@echo "  all          - Build all documentation (man + info)"
	@echo "  man          - Prepare man pages"
	@echo "  info         - Build info pages from texinfo"
	@echo "  install-man  - Install man pages to DESTDIR"
	@echo "  install-info - Install info pages to DESTDIR"
	@echo "  test-man     - View man pages locally without installing"
	@echo "  clean        - Remove generated files"
	@echo "  help         - Show this help message"
