# Makefile for Repo Remap Claude Skill
# Packages the repository into a distributable Claude skill format

SKILL_NAME := repo-remap
VERSION := $(shell cat VERSION)
BUILD_DIR := build
DIST_DIR := dist
PYTHON ?= python3

# Local install destination for the opt-in sync-skill target (writes to $HOME)
SKILL_INSTALL_DIR := $(HOME)/.claude/skills/$(SKILL_NAME)

# Files to include in the skill package. SCRIPT_FILES is explicit on purpose:
# check_*.py gates and test_*.py suites are dev-only and must never ship or sync.
SKILL_FILE := src/SKILL.md
SCRIPT_FILES := src/scripts/module_tree.py
DOC_FILES := README.md LICENSE CHANGELOG.md VERSION

# Default target
.PHONY: all
all: package

# Build the skill package structure
.PHONY: build
build:
	@echo "Building skill package: $(SKILL_NAME)"
	mkdir -p $(BUILD_DIR)/$(SKILL_NAME)/scripts
	cp $(SKILL_FILE) $(BUILD_DIR)/$(SKILL_NAME)/
	sed -i "s/__SKILL_VERSION__/$(VERSION)/g" $(BUILD_DIR)/$(SKILL_NAME)/SKILL.md
	sed -i "s/__SKILL_DATE__/$$(date -u +%Y-%m-%d)/g" $(BUILD_DIR)/$(SKILL_NAME)/SKILL.md
	sed -i "s/__SKILL_COMMIT__/$$(git rev-parse --short HEAD)/g" $(BUILD_DIR)/$(SKILL_NAME)/SKILL.md
	cp $(SCRIPT_FILES) $(BUILD_DIR)/$(SKILL_NAME)/scripts/
	cp $(DOC_FILES) $(BUILD_DIR)/$(SKILL_NAME)/
	@echo "Build complete: $(BUILD_DIR)/$(SKILL_NAME)"

# Create a combined single-file skill (SKILL.md only, for pasting into context)
.PHONY: build-combined
build-combined:
	@echo "Building combined single-file skill..."
	mkdir -p $(BUILD_DIR)
	cp $(SKILL_FILE) $(BUILD_DIR)/$(SKILL_NAME)-combined.md
	@echo "" >> $(BUILD_DIR)/$(SKILL_NAME)-combined.md
	@echo "---" >> $(BUILD_DIR)/$(SKILL_NAME)-combined.md
	@echo "" >> $(BUILD_DIR)/$(SKILL_NAME)-combined.md
	@# The Note sits at the END because SKILL.md's YAML frontmatter must remain the file's
	@# first bytes. Keep byte-identical to build.ps1's note: test_build_channels.py pins the pair.
	@echo "> **Note**: This combined file is a PASTE-INTO-CONTEXT artifact, not an installed skill." >> $(BUILD_DIR)/$(SKILL_NAME)-combined.md
	@echo "> It ships no scripts, so \`python3 <skill-path>/scripts/module_tree.py\` is not runnable" >> $(BUILD_DIR)/$(SKILL_NAME)-combined.md
	@echo "> as written. Use the manual mapping fallback in Step 0: list directories, count direct" >> $(BUILD_DIR)/$(SKILL_NAME)-combined.md
	@echo "> files, discard ignored paths, sort by path depth descending. The zip or tarball" >> $(BUILD_DIR)/$(SKILL_NAME)-combined.md
	@echo "> package includes the script." >> $(BUILD_DIR)/$(SKILL_NAME)-combined.md
	sed -i "s/__SKILL_VERSION__/$(VERSION)/g" $(BUILD_DIR)/$(SKILL_NAME)-combined.md
	sed -i "s/__SKILL_DATE__/$$(date -u +%Y-%m-%d)/g" $(BUILD_DIR)/$(SKILL_NAME)-combined.md
	sed -i "s/__SKILL_COMMIT__/$$(git rev-parse --short HEAD)/g" $(BUILD_DIR)/$(SKILL_NAME)-combined.md
	@echo "Combined skill created: $(BUILD_DIR)/$(SKILL_NAME)-combined.md"

# Package as zip for distribution
.PHONY: package
package: validate build
	@echo "Packaging skill as zip..."
	mkdir -p $(DIST_DIR)
	cd $(BUILD_DIR) && zip -r ../$(DIST_DIR)/$(SKILL_NAME)-v$(VERSION).zip $(SKILL_NAME)
	@echo "Package created: $(DIST_DIR)/$(SKILL_NAME)-v$(VERSION).zip"

# Package combined single-file version
.PHONY: package-combined
package-combined: validate build-combined
	mkdir -p $(DIST_DIR)
	cp $(BUILD_DIR)/$(SKILL_NAME)-combined.md $(DIST_DIR)/
	@echo "Combined skill copied to: $(DIST_DIR)/$(SKILL_NAME)-combined.md"

# Create tarball
.PHONY: package-tar
package-tar: validate build
	@echo "Packaging skill as tarball..."
	mkdir -p $(DIST_DIR)
	cd $(BUILD_DIR) && tar -czvf ../$(DIST_DIR)/$(SKILL_NAME)-v$(VERSION).tar.gz $(SKILL_NAME)
	@echo "Package created: $(DIST_DIR)/$(SKILL_NAME)-v$(VERSION).tar.gz"

# Validate skill structure. Fast and suite-free: the test suite runs under `test`.
.PHONY: validate
validate:
	@echo "Validating skill structure..."
	@test -f $(SKILL_FILE) || { echo "ERROR: $(SKILL_FILE) not found"; exit 1; }
	@grep -q "^name:" $(SKILL_FILE) || { echo "ERROR: SKILL.md missing 'name' in frontmatter"; exit 1; }
	@grep -q "^description:" $(SKILL_FILE) || { echo "ERROR: SKILL.md missing 'description' in frontmatter"; exit 1; }
	@test -d src/scripts || { echo "ERROR: src/scripts/ directory not found"; exit 1; }
	@# Build-time placeholders must be present in source; build substitutes them.
	@echo "Checking version placeholders..."
	@# Inside a loop, write `|| { echo "ERROR: ..."; exit 1; }`. Never `|| (echo ... && exit 1)`:
	@# `exit 1` in a `( )` subshell ends only that subshell, and a `for` loop's exit status is
	@# its LAST iteration's, so an earlier failure would print ERROR and the recipe still pass.
	@for tok in __SKILL_VERSION__ __SKILL_DATE__ __SKILL_COMMIT__; do \
		grep -q "$$tok" $(SKILL_FILE) || { echo "ERROR: $(SKILL_FILE) missing placeholder $$tok"; exit 1; }; \
	done
	@# Every scripts/<x>.py cited in SKILL.md must exist under src/scripts/
	@echo "Checking script citations..."
	@for ref in $$(grep -oE 'scripts/[a-z0-9_]+\.py' $(SKILL_FILE) | sort -u); do \
		test -f "src/$$ref" || { echo "ERROR: $(SKILL_FILE) cites $$ref but src/$$ref not found"; exit 1; }; \
	done
	@echo "Checking README badge parity (version + test count)..."
	@$(PYTHON) src/scripts/check_readme_parity.py || exit 1
	@echo "Checking CHANGELOG parity (top entry <-> VERSION)..."
	@$(PYTHON) src/scripts/check_changelog_parity.py || exit 1
	@echo "Checking ignore-list parity (README <-> module_tree.py)..."
	@$(PYTHON) src/scripts/check_ignore_parity.py || exit 1
	@echo "Validation passed!"

# Check script syntax. Standard library only by design: do not add linters that need pip.
.PHONY: lint
lint:
	@echo "Checking script syntax..."
	$(PYTHON) -m py_compile src/scripts/check_changelog_parity.py
	$(PYTHON) -m py_compile src/scripts/check_ignore_parity.py
	$(PYTHON) -m py_compile src/scripts/check_readme_parity.py
	$(PYTHON) -m py_compile src/scripts/check_test_count.py
	$(PYTHON) -m py_compile src/scripts/module_tree.py
	$(PYTHON) -m py_compile src/scripts/test_build_channels.py
	$(PYTHON) -m py_compile src/scripts/test_check_changelog_parity.py
	$(PYTHON) -m py_compile src/scripts/test_check_ignore_parity.py
	$(PYTHON) -m py_compile src/scripts/test_check_readme_parity.py
	$(PYTHON) -m py_compile src/scripts/test_check_test_count.py
	$(PYTHON) -m py_compile src/scripts/test_module_tree.py
	@echo "Syntax check passed!"

# Run tests, then compare TEST_COUNT against the live pass count.
# check_test_count.py is wired here and NOT into `validate`: it re-runs the suite.
# Keep this target in lockstep with build.ps1's Invoke-Test.
.PHONY: test
test: lint
	@echo "Running test suite..."
	$(PYTHON) -m unittest discover -s src/scripts -p "test_*.py"
	@echo "Checking TEST_COUNT against the live suite result..."
	$(PYTHON) src/scripts/check_test_count.py
	@echo "Tests passed!"

# Clean build artifacts
.PHONY: clean
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILD_DIR)
	rm -rf $(DIST_DIR)
	rm -rf src/scripts/__pycache__
	@echo "Clean complete"

# Show package contents
.PHONY: list
list: build
	@echo "Package contents:"
	@find $(BUILD_DIR)/$(SKILL_NAME) -type f | sort

# Opt-in: deploy repo source to the local installed skill (writes to $HOME). Not a prereq of build/package.
# Prune before copy: `cp` alone cannot remove a file that was DELETED from the repo, so a
# copy-only sync leaves orphans behind forever. The scripts dir is wholly owned by this skill.
.PHONY: sync-skill
sync-skill:
	@echo "Syncing repo source to local installed skill: $(SKILL_INSTALL_DIR)"
	mkdir -p $(SKILL_INSTALL_DIR)/scripts
	rm -f $(SKILL_INSTALL_DIR)/scripts/*.py
	cp $(SKILL_FILE) $(SKILL_INSTALL_DIR)/SKILL.md
	cp $(SCRIPT_FILES) $(SKILL_INSTALL_DIR)/scripts/
	cp $(DOC_FILES) $(SKILL_INSTALL_DIR)/
	@test -z "$$(ls $(SKILL_INSTALL_DIR)/scripts/test_*.py $(SKILL_INSTALL_DIR)/scripts/check_*.py 2>/dev/null)" || { echo "ERROR: sync-skill shipped dev-only scripts into the install"; exit 1; }
	@diff -q $(SKILL_FILE) $(SKILL_INSTALL_DIR)/SKILL.md \
	  && diff -q src/scripts/module_tree.py $(SKILL_INSTALL_DIR)/scripts/module_tree.py \
	  && diff -q VERSION $(SKILL_INSTALL_DIR)/VERSION \
	  && echo "Sync verified (SKILL.md, module_tree.py, VERSION)." \
	  || { echo "ERROR: sync diff mismatch"; exit 1; }

# Help
.PHONY: help
help:
	@echo "Repo Remap Skill - Makefile targets:"
	@echo ""
	@echo "  make build            - Build skill package structure"
	@echo "  make build-combined   - Build single-file skill (SKILL.md only)"
	@echo "  make package          - Create zip package (default)"
	@echo "  make package-combined - Create single-file skill package"
	@echo "  make package-tar      - Create tarball package"
	@echo "  make validate         - Validate skill structure and parity gates"
	@echo "  make lint             - Check script syntax"
	@echo "  make test             - Run tests and the TEST_COUNT gate"
	@echo "  make clean            - Remove build artifacts"
	@echo "  make list             - Show package contents"
	@echo "  make sync-skill       - Opt-in: deploy repo source to local installed skill (writes to \$$HOME)"
	@echo "  make help             - Show this help"
	@echo ""
	@echo "Skill: $(SKILL_NAME) v$(VERSION)"
