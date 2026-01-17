.PHONY: help fixtures fixtures-clean

help:
	@echo "CruxMD v2 - Development Commands"
	@echo ""
	@echo "Fixtures:"
	@echo "  make fixtures        Generate Synthea patient fixtures (5 patients)"
	@echo "  make fixtures-clean  Remove generated fixtures"
	@echo ""

# Generate Synthea patient fixtures using Docker
fixtures:
	@echo "Generating Synthea fixtures..."
	python scripts/generate_fixtures.py --count 5 --output fixtures/synthea

# Clean generated fixtures
fixtures-clean:
	@echo "Removing fixtures..."
	rm -rf fixtures/synthea/*.json
