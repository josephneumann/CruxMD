#!/usr/bin/env python3
"""
Generate test fixtures from Synthea using Docker.

Usage:
    python scripts/generate_fixtures.py                    # Default: 5 patients
    python scripts/generate_fixtures.py --count 10         # Custom count
    python scripts/generate_fixtures.py --output data/     # Custom output dir

Run locally, commit results to repo for deterministic CI tests.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SYNTHEA_SEED = 12345  # Deterministic: same seed = same patients
SYNTHEA_IMAGE = "cruxmd-synthea:local"
DEFAULT_OUTPUT = Path("fixtures/synthea")
DOCKERFILE_PATH = Path(__file__).parent / "Dockerfile.synthea"


def check_docker() -> bool:
    """Verify Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def build_synthea_image() -> bool:
    """Build the Synthea Docker image from local Dockerfile."""
    print(f"Building Synthea image: {SYNTHEA_IMAGE}")

    if not DOCKERFILE_PATH.exists():
        print(f"Dockerfile not found: {DOCKERFILE_PATH}")
        return False

    result = subprocess.run(
        [
            "docker", "build",
            "-t", SYNTHEA_IMAGE,
            "-f", str(DOCKERFILE_PATH),
            str(DOCKERFILE_PATH.parent),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Failed to build image: {result.stderr}")
        return False
    print("Image built successfully")
    return True


def generate_patients(count: int, output_dir: Path) -> bool:
    """
    Generate Synthea patients with deterministic seed using Docker.

    Returns True if generation succeeded, False otherwise.
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use a temp directory for raw Synthea output
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    # Run Synthea in Docker
    # Synthea outputs to /output inside the container
    print(f"Generating {count} patients with seed {SYNTHEA_SEED}...")

    # The entrypoint already includes: java -jar synthea.jar --exporter.baseDirectory /output
    # We just need to add the patient generation args
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{raw_dir.absolute()}:/output",
        SYNTHEA_IMAGE,
        "-p", str(count),
        "-s", str(SYNTHEA_SEED),
        "--exporter.fhir.export", "true",
        "--exporter.fhir.bulk_data", "false",
        "--exporter.ccda.export", "false",
        "--exporter.csv.export", "false",
        "--exporter.hospital.fhir.export", "false",
        "--exporter.practitioner.fhir.export", "false",
    ]

    print(f"Running: {' '.join(docker_cmd)}")
    result = subprocess.run(docker_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Synthea generation failed: {result.stderr}")
        return False

    print(result.stdout)

    # Find and copy FHIR bundles
    fhir_dir = raw_dir / "fhir"
    if not fhir_dir.exists():
        print(f"FHIR output directory not found: {fhir_dir}")
        print(f"Raw dir contents: {list(raw_dir.iterdir())}")
        return False

    bundle_count = 0
    for i, bundle_path in enumerate(sorted(fhir_dir.glob("*.json"))):
        # Skip hospital and practitioner bundles
        name_lower = bundle_path.name.lower()
        if "hospital" in name_lower or "practitioner" in name_lower:
            continue

        # Copy to numbered fixture file
        dest = output_dir / f"patient_bundle_{bundle_count + 1}.json"
        shutil.copy(bundle_path, dest)

        # Validate it's a proper FHIR Bundle
        with open(dest) as f:
            bundle = json.load(f)
            if bundle.get("resourceType") != "Bundle":
                print(f"Warning: {dest} is not a FHIR Bundle")
                continue

            entry_count = len(bundle.get("entry", []))
            print(f"Created: {dest.name} ({entry_count} resources)")

        bundle_count += 1
        if bundle_count >= count:
            break

    # Cleanup raw output
    shutil.rmtree(raw_dir)

    print(f"\nGenerated {bundle_count} patient fixtures in {output_dir}")
    return bundle_count == count


def main():
    parser = argparse.ArgumentParser(
        description="Generate Synthea patient fixtures using Docker"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of patients to generate (default: 5)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    # Verify Docker is available
    if not check_docker():
        print("Error: Docker is not running or not installed")
        print("Please install Docker and ensure the daemon is running")
        sys.exit(1)

    # Build Synthea image if needed
    if not build_synthea_image():
        print("Error: Could not build Synthea Docker image")
        sys.exit(1)

    # Generate patients
    if not generate_patients(args.count, args.output):
        print("Error: Patient generation failed")
        sys.exit(1)

    print("\nFixture generation complete!")


if __name__ == "__main__":
    main()
