"""Seed database with Synthea patient fixtures and profiles.

Loads all patient bundles from fixtures/synthea/ into PostgreSQL and Neo4j,
embedding narrative profiles as FHIR extensions on Patient resources.

Usage:
    uv run python -m app.scripts.seed_database

The script is idempotent - it can be run multiple times safely.
Existing resources are updated via MERGE/upsert semantics.
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import text

from app.database import async_session_maker, engine
from app.services.fhir_loader import load_bundle_with_profile
from app.services.graph import KnowledgeGraph


async def verify_connections(graph: KnowledgeGraph) -> bool:
    """Verify database connections are working."""
    # Check PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("  PostgreSQL: connected")
    except Exception as e:
        print(f"  PostgreSQL: FAILED - {e}")
        return False

    # Check Neo4j
    try:
        connected = await graph.verify_connectivity()
        if connected:
            print("  Neo4j: connected")
        else:
            print("  Neo4j: FAILED - could not verify connectivity")
            return False
    except Exception as e:
        print(f"  Neo4j: FAILED - {e}")
        return False

    return True


async def seed_database(fixtures_dir: Path) -> dict[str, int]:
    """
    Seed database with all patient fixtures.

    Args:
        fixtures_dir: Path to fixtures/synthea directory.

    Returns:
        Dictionary with counts: patients_loaded, resources_loaded.
    """
    stats = {"patients_loaded": 0, "resources_loaded": 0}

    # Find all patient bundle files
    bundle_files = sorted(fixtures_dir.glob("patient_bundle_*.json"))
    bundle_files = [f for f in bundle_files if ".profile." not in f.name]

    if not bundle_files:
        print(f"No patient bundles found in {fixtures_dir}")
        return stats

    print(f"Found {len(bundle_files)} patient bundles")

    # Initialize graph service
    graph = KnowledgeGraph()

    try:
        # Verify connections
        print("\nVerifying database connections...")
        if not await verify_connections(graph):
            raise RuntimeError("Database connection verification failed")

        print("\nLoading patient bundles...")

        for bundle_path in bundle_files:
            print(f"\n  Loading {bundle_path.name}...")

            # Load bundle
            with open(bundle_path) as f:
                bundle = json.load(f)

            # Load corresponding profile if it exists
            profile_path = bundle_path.with_suffix(".profile.json")
            profile = None
            if profile_path.exists():
                with open(profile_path) as f:
                    profile = json.load(f)
                print(f"    Found profile: {profile_path.name}")

            # Count resources in bundle
            resource_count = len(bundle.get("entry", []))

            # Load into databases
            async with async_session_maker() as session:
                patient_id = await load_bundle_with_profile(
                    db=session,
                    graph=graph,
                    bundle=bundle,
                    profile=profile,
                    generate_embeddings=False,  # Embeddings not implemented yet
                )
                await session.commit()

            print(f"    Patient ID: {patient_id}")
            print(f"    Resources: {resource_count}")

            stats["patients_loaded"] += 1
            stats["resources_loaded"] += resource_count

    finally:
        await graph.close()

    return stats


def main() -> None:
    """Main entry point for the seed script."""
    # Resolve fixtures directory relative to repo root
    repo_root = Path(__file__).parent.parent.parent.parent
    fixtures_dir = repo_root / "fixtures" / "synthea"

    if not fixtures_dir.exists():
        print(f"Fixtures directory not found: {fixtures_dir}")
        print("Run fixture generation first (Stories 4.1 and 4.2)")
        return

    print("=" * 50)
    print("CruxMD Database Seeding")
    print("=" * 50)

    stats = asyncio.run(seed_database(fixtures_dir))

    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"  Patients loaded: {stats['patients_loaded']}")
    print(f"  Resources loaded: {stats['resources_loaded']}")
    print("\nDatabase seeding complete!")


if __name__ == "__main__":
    main()
